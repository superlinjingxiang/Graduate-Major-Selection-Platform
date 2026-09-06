from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from gradmatch.accounts.models import User
from gradmatch.advising.comparison import recompute_comparison_run
from gradmatch.advising.models import (
    ComparisonRun,
    ComparisonRunResult,
    DecisionSnapshot,
    EligibilityRule,
    EvidenceClaimRevision,
    GuestSession,
    PublicationEvent,
    ReviewDecision,
    RuleEvidenceUsage,
    RuleSetRevision,
    SourceDocumentRevision,
)
from gradmatch.advising.publication import publish_claim, publish_rule_set, revise_claim
from gradmatch.catalog.models import AnnualOffering

from .models import AuditEvent, CorrectionCase, JobExecution, OutboxEvent, SnapshotUpdate

RECOMPUTATION_HANDLER = "support.recompute_published_correction"
CORRECTION_PUBLICATION_EVENT = "correction.claim_published"


class CorrectionWorkflowError(RuntimeError):
    pass


@transaction.atomic
def submit_correction(
    *,
    offering: AnnualOffering,
    field_key: str,
    proposed_source_url: str,
    explanation: str,
    submitter: User | None = None,
    guest_session: GuestSession | None = None,
) -> CorrectionCase:
    if (submitter is None) == (guest_session is None):
        raise CorrectionWorkflowError(
            "A correction requires exactly one account or guest submitter."
        )
    return CorrectionCase.objects.create(
        offering=offering,
        field_key=field_key,
        proposed_source_url=proposed_source_url,
        explanation=explanation,
        submitter=submitter,
        guest_session=guest_session,
    )


@transaction.atomic
def accept_correction(
    *,
    correction_id: UUID | str,
    reviewer: User,
    source_document: SourceDocumentRevision,
    normalized_value: object,
    original_value: str,
    reviewer_note: str,
    now: datetime,
) -> CorrectionCase:
    _require_staff(reviewer)
    case = CorrectionCase.objects.select_for_update().select_related("offering").get(
        pk=correction_id
    )
    if case.status != CorrectionCase.Status.SUBMITTED.value:
        raise CorrectionWorkflowError("Only a submitted correction can be accepted.")
    if (
        source_document.data_class != SourceDocumentRevision.DataClass.PRODUCTION.value
        or source_document.reference_year != case.offering.target_year
    ):
        raise CorrectionWorkflowError(
            "A production correction requires current-year production evidence."
        )
    original_claim = (
        EvidenceClaimRevision.objects.filter(
            offering=case.offering,
            field_key=case.field_key,
            publication_event__isnull=False,
            superseded_by__isnull=True,
        )
        .order_by("-revision", "-id")
        .first()
    )
    if original_claim is None:
        raise CorrectionWorkflowError("No published claim exists for this correction target.")

    replacement = revise_claim(
        claim_id=original_claim.pk,
        source_document=source_document,
        normalized_value=normalized_value,
        original_value=original_value,
    )
    ReviewDecision.objects.create(
        claim=replacement,
        reviewer=reviewer,
        outcome=ReviewDecision.Outcome.APPROVED,
        note=reviewer_note,
    )
    case.accepted_claim = replacement
    case.reviewer_note = reviewer_note
    case.status = CorrectionCase.Status.ACCEPTED.value
    case.save(update_fields=("accepted_claim", "reviewer_note", "status", "updated_at"))
    AuditEvent.objects.create(
        actor=reviewer,
        action="correction.accepted",
        target_type="correction_case",
        target_id=str(case.pk),
        metadata={
            "claim_id": replacement.pk,
            "superseded_claim_id": original_claim.pk,
            "reviewed_at": now.isoformat(),
        },
    )
    return case


@transaction.atomic
def publish_correction(
    *,
    correction_id: UUID | str,
    reviewer: User,
    now: datetime,
) -> OutboxEvent:
    _require_staff(reviewer)
    case = CorrectionCase.objects.select_for_update().select_related(
        "accepted_claim__supersedes"
    ).get(pk=correction_id)
    if case.status == CorrectionCase.Status.PUBLISHED.value:
        publication = PublicationEvent.objects.filter(claim=case.accepted_claim).first()
        event = (
            OutboxEvent.objects.filter(
                event_key=f"correction.claim-published:{publication.pk}",
                event_type=CORRECTION_PUBLICATION_EVENT,
            ).first()
            if publication is not None
            else None
        )
        if event is None:
            raise CorrectionWorkflowError("The published correction is missing its outbox event.")
        return event
    if case.status != CorrectionCase.Status.ACCEPTED.value or case.accepted_claim is None:
        raise CorrectionWorkflowError("A correction must be accepted before publication.")
    if case.accepted_claim.supersedes is None:
        raise CorrectionWorkflowError("The accepted claim must supersede a published revision.")

    publication = publish_claim(
        claim_id=case.accepted_claim.pk,
        reviewer=reviewer,
        now=now,
    )
    revised_rule_set_ids = _create_revalidation_rule_sets(
        superseded_claim=case.accepted_claim.supersedes,
        replacement_claim=case.accepted_claim,
        reviewer=reviewer,
        now=now,
    )
    payload: dict[str, object] = {
        "correction_id": str(case.pk),
        "publication_event_id": publication.pk,
        "superseded_claim_id": case.accepted_claim.supersedes.pk,
        "replacement_claim_id": case.accepted_claim.pk,
        "revised_rule_set_ids": revised_rule_set_ids,
    }
    outbox = OutboxEvent.objects.create(
        event_key=f"correction.claim-published:{publication.pk}",
        event_type=CORRECTION_PUBLICATION_EVENT,
        payload=payload,
        published_at=now,
    )
    case.status = CorrectionCase.Status.PUBLISHED.value
    case.save(update_fields=("status", "updated_at"))
    AuditEvent.objects.create(
        actor=reviewer,
        action="correction.published",
        target_type="correction_case",
        target_id=str(case.pk),
        metadata={
            "publication_event_id": publication.pk,
            "outbox_event_key": outbox.event_key,
            "published_at": now.isoformat(),
        },
    )
    return outbox


def _create_revalidation_rule_sets(
    *,
    superseded_claim: EvidenceClaimRevision,
    replacement_claim: EvidenceClaimRevision,
    reviewer: User,
    now: datetime,
) -> list[int]:
    published_rule_sets = list(select_published_rule_sets_for_update(superseded_claim))
    revised_ids: list[int] = []
    for previous in published_rule_sets:
        latest = (
            RuleSetRevision.objects.filter(key=previous.key)
            .order_by("-revision", "-id")
            .first()
        )
        next_revision = previous.revision + 1 if latest is None else latest.revision + 1
        revised = RuleSetRevision.objects.create(
            key=previous.key,
            revision=next_revision,
            namespace=previous.namespace,
            target_year=previous.target_year,
            reference_year=previous.reference_year,
            manifest=previous.manifest,
            status=RuleSetRevision.Status.DRAFT.value,
            coverage_complete=False,
        )
        for previous_rule in EligibilityRule.objects.filter(rule_set=previous).order_by(
            "position", "id"
        ):
            revised_rule = EligibilityRule.objects.create(
                rule_set=revised,
                key=previous_rule.key,
                position=previous_rule.position,
                fact_key=previous_rule.fact_key,
                operator=previous_rule.operator,
                expected_value=previous_rule.expected_value,
                failure_reason_code=previous_rule.failure_reason_code,
            )
            for usage in RuleEvidenceUsage.objects.filter(rule=previous_rule).order_by(
                "claim_id"
            ):
                RuleEvidenceUsage.objects.create(
                    rule=revised_rule,
                    claim=(
                        replacement_claim
                        if usage.claim.pk == superseded_claim.pk
                        else usage.claim
                    ),
                )
        publish_rule_set(rule_set_id=revised.pk, reviewer=reviewer, now=now)
        revised_ids.append(revised.pk)
    return revised_ids


def select_published_rule_sets_for_update(
    claim: EvidenceClaimRevision,
) -> QuerySet[RuleSetRevision]:
    matching_ids = RuleEvidenceUsage.objects.filter(claim=claim).values_list(
        "rule__rule_set_id",
        flat=True,
    )
    return (
        RuleSetRevision.objects.select_for_update()
        .filter(
            pk__in=matching_ids,
            namespace=RuleSetRevision.Namespace.PRODUCTION.value,
            status=RuleSetRevision.Status.PUBLISHED.value,
        )
        .order_by("key", "revision")
    )


@transaction.atomic
def reject_correction(
    *,
    correction_id: UUID | str,
    reviewer: User,
    reviewer_note: str,
    now: datetime,
) -> CorrectionCase:
    _require_staff(reviewer)
    case = CorrectionCase.objects.select_for_update().get(pk=correction_id)
    if case.status != CorrectionCase.Status.SUBMITTED.value:
        raise CorrectionWorkflowError("Only a submitted correction can be rejected.")
    case.status = CorrectionCase.Status.REJECTED.value
    case.reviewer_note = reviewer_note
    case.save(update_fields=("status", "reviewer_note", "updated_at"))
    AuditEvent.objects.create(
        actor=reviewer,
        action="correction.rejected",
        target_type="correction_case",
        target_id=str(case.pk),
        metadata={"reviewed_at": now.isoformat()},
    )
    return case


@transaction.atomic
def process_recomputation_event(*, event_key: str) -> dict[str, int]:
    event = OutboxEvent.objects.select_for_update().get(
        event_key=event_key,
        event_type=CORRECTION_PUBLICATION_EVENT,
    )
    existing = JobExecution.objects.filter(
        event_key=event.event_key,
        handler_name=RECOMPUTATION_HANDLER,
        status=JobExecution.Status.SUCCEEDED.value,
    ).first()
    if existing is not None:
        return _execution_result(existing.result)

    execution = JobExecution.objects.create(
        event_key=event.event_key,
        handler_name=RECOMPUTATION_HANDLER,
        status=JobExecution.Status.RUNNING.value,
        started_at=timezone.now(),
    )
    publication_event_id = _payload_int(event.payload, "publication_event_id")
    superseded_claim_id = _payload_int(event.payload, "superseded_claim_id")
    publication = PublicationEvent.objects.get(pk=publication_event_id)
    affected_runs = list(
        ComparisonRun.objects.filter(
            results__assessment_usages__assessment__rule_set__rules__evidence_usages__claim_id=(
                superseded_claim_id
            )
        )
        .distinct()
        .order_by("created_at", "id")
    )

    created_results = 0
    created_snapshot_updates = 0
    for run in affected_runs:
        old_result = ComparisonRunResult.objects.filter(run=run).order_by("-version").first()
        if old_result is None:
            continue
        new_result, created = recompute_comparison_run(
            run=run,
            trigger_publication_event=publication,
        )
        if not created:
            continue
        created_results += 1
        snapshot = (
            DecisionSnapshot.objects.filter(comparison_result=old_result)
            .order_by("-created_at", "-id")
            .first()
        )
        if snapshot is not None:
            _, update_created = SnapshotUpdate.objects.get_or_create(
                outbox_event=event,
                old_snapshot=snapshot,
                defaults={
                    "old_result": old_result,
                    "new_result": new_result,
                    "diff": _comparison_diff(old_result, new_result),
                },
            )
            created_snapshot_updates += int(update_created)

    result: dict[str, object] = {
        "affected_runs": len(affected_runs),
        "created_results": created_results,
        "created_snapshot_updates": created_snapshot_updates,
    }
    completed_at = timezone.now()
    execution.status = JobExecution.Status.SUCCEEDED.value
    execution.result = result
    execution.completed_at = completed_at
    execution.save(update_fields=("status", "result", "completed_at"))
    event.processing_state = OutboxEvent.ProcessingState.PROCESSED.value
    event.processed_at = completed_at
    event.save(update_fields=("processing_state", "processed_at"))
    return _execution_result(result)


def _comparison_diff(
    old_result: ComparisonRunResult,
    new_result: ComparisonRunResult,
) -> dict[str, object]:
    old_groups = _groups(old_result)
    new_groups = _groups(new_result)
    group_changes: dict[str, object] = {}
    for key in ("eligible_known", "ineligible_known", "needs_confirmation"):
        old_values = set(old_groups[key])
        new_values = set(new_groups[key])
        group_changes[key] = {
            "added": sorted(new_values - old_values),
            "removed": sorted(old_values - new_values),
        }
    return {
        "from_result_hash": old_result.result_hash,
        "to_result_hash": new_result.result_hash,
        "group_changes": group_changes,
    }


def _groups(result: ComparisonRunResult) -> dict[str, list[str]]:
    raw_groups = result.result.get("groups")
    if not isinstance(raw_groups, dict):
        raise CorrectionWorkflowError("A persisted comparison result has invalid groups.")
    groups = cast(dict[str, object], raw_groups)
    normalized: dict[str, list[str]] = {}
    for key in ("eligible_known", "ineligible_known", "needs_confirmation"):
        raw_values = groups.get(key)
        if not isinstance(raw_values, list):
            raise CorrectionWorkflowError("A persisted comparison result has invalid groups.")
        values = cast(list[object], raw_values)
        if not all(isinstance(value, str) for value in values):
            raise CorrectionWorkflowError("A persisted comparison result has invalid groups.")
        normalized[key] = cast(list[str], values)
    return normalized


def _execution_result(payload: dict[str, object]) -> dict[str, int]:
    return {
        "affected_runs": _payload_int(payload, "affected_runs"),
        "created_results": _payload_int(payload, "created_results"),
        "created_snapshot_updates": _payload_int(payload, "created_snapshot_updates"),
    }


def _payload_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise CorrectionWorkflowError(f"Outbox payload field '{key}' must be an integer.")
    return value


def _require_staff(reviewer: User) -> None:
    if not User.objects.filter(pk=reviewer.pk, is_staff=True).exists():
        raise CorrectionWorkflowError("Only staff reviewers may change correction status.")
