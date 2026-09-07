from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from gradmatch.accounts.models import User
from gradmatch.accounts.roles import (
    ADMINISTRATOR_ROLE,
    EDITOR_ROLE,
    REVIEWER_ROLE,
    has_staff_role,
)
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
from gradmatch.catalog.models import AnnualOffering, CoverageManifest
from gradmatch.catalog.seed import ENGINEERING_SLICE_OFFERING_IDS, PILOT_MANIFEST_KEY

from .models import (
    AuditEvent,
    CorrectionCase,
    JobExecution,
    OutboxEvent,
    SnapshotUpdate,
    SnapshotUpdateNotification,
)

RECOMPUTATION_HANDLER = "support.recompute_published_correction"
CORRECTION_PUBLICATION_EVENT = "correction.claim_published"
OUTBOX_DISPATCH_RETRY_AFTER = timedelta(minutes=5)


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
def begin_correction_review(
    *,
    correction_id: UUID | str,
    reviewer: User,
    now: datetime,
) -> CorrectionCase:
    _require_role(reviewer, REVIEWER_ROLE)
    case = CorrectionCase.objects.select_for_update().get(pk=correction_id)
    if case.status == CorrectionCase.Status.REVIEWING.value:
        if case.reviewer is None or case.reviewer.pk != reviewer.pk:
            raise CorrectionWorkflowError(
                "A correction already has a different assigned reviewer."
            )
        return case
    if case.status != CorrectionCase.Status.SUBMITTED.value:
        raise CorrectionWorkflowError("Only a submitted correction can enter review.")
    case.status = CorrectionCase.Status.REVIEWING.value
    case.reviewer = reviewer
    case.review_started_at = now
    case.save(
        update_fields=("status", "reviewer", "review_started_at", "updated_at")
    )
    AuditEvent.objects.create(
        actor=reviewer,
        action="correction.review_started",
        target_type="correction_case",
        target_id=str(case.pk),
        metadata={"review_started_at": now.isoformat()},
    )
    return case


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
    _require_role(reviewer, REVIEWER_ROLE)
    case = CorrectionCase.objects.select_for_update().select_related("offering").get(
        pk=correction_id
    )
    _require_assigned_review(case, reviewer)
    if (
        source_document.data_class != SourceDocumentRevision.DataClass.PRODUCTION.value
        or source_document.reference_year != case.offering.target_year
    ):
        raise CorrectionWorkflowError(
            "A production correction requires current-year production evidence."
        )
    if source_document.created_by is None or not has_staff_role(
        source_document.created_by, EDITOR_ROLE
    ):
        raise CorrectionWorkflowError(
            "A correction replacement requires a creator with the editor role."
        )
    if source_document.created_by.pk == reviewer.pk:
        raise CorrectionWorkflowError("A correction replacement requires an independent reviewer.")
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
    _require_role(reviewer, ADMINISTRATOR_ROLE)
    # Serialise publication against one stable row so every event can capture a
    # complete, globally ordered production-rule state.
    CoverageManifest.objects.select_for_update().get(key=PILOT_MANIFEST_KEY)
    case = CorrectionCase.objects.select_for_update(of=("self",)).select_related(
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
    predecessor = OutboxEvent.objects.filter(
        event_type=CORRECTION_PUBLICATION_EVENT,
    ).order_by("-id").first()
    payload: dict[str, object] = {
        "correction_id": str(case.pk),
        "publication_event_id": publication.pk,
        "superseded_claim_id": case.accepted_claim.supersedes.pk,
        "replacement_claim_id": case.accepted_claim.pk,
        "revised_rule_set_ids": revised_rule_set_ids,
        "predecessor_event_key": predecessor.event_key if predecessor is not None else None,
        "rule_set_ids_by_offering": _current_rule_set_ids_by_offering(),
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
    # The offering row is the stable serialization point for every production
    # rule-set family that can reference one of its claims. Unlike an immutable
    # revision row, it remains the same while newer revisions are appended.
    AnnualOffering.objects.select_for_update().get(pk=replacement_claim.offering.pk)
    affected_keys = sorted(
        set(
            select_published_rule_sets_for_update(superseded_claim).values_list(
                "key", flat=True
            )
        )
    )
    revised_ids: list[int] = []
    for key in affected_keys:
        previous = (
            RuleSetRevision.objects.select_for_update()
            .filter(
                key=key,
                namespace=RuleSetRevision.Namespace.PRODUCTION.value,
                status=RuleSetRevision.Status.PUBLISHED.value,
            )
            .order_by("-revision", "-id")
            .first()
        )
        if previous is None or not RuleEvidenceUsage.objects.filter(
            rule__rule_set=previous,
            claim=superseded_claim,
        ).exists():
            continue
        latest_any = (
            RuleSetRevision.objects.select_for_update()
            .filter(key=key)
            .order_by("-revision", "-id")
            .first()
        )
        if latest_any is None:
            raise CorrectionWorkflowError("The published rule-set family is missing.")
        revised = RuleSetRevision.objects.create(
            key=previous.key,
            revision=latest_any.revision + 1,
            namespace=previous.namespace,
            target_year=previous.target_year,
            reference_year=previous.reference_year,
            manifest=previous.manifest,
            status=RuleSetRevision.Status.DRAFT.value,
            coverage_complete=False,
            created_by=replacement_claim.created_by,
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
    _require_role(reviewer, REVIEWER_ROLE)
    case = CorrectionCase.objects.select_for_update().get(pk=correction_id)
    _require_assigned_review(case, reviewer)
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


def dispatch_pending_outbox_events(*, now: datetime, limit: int = 50) -> int:
    """Lease and enqueue pending events; unfinished leases become retryable."""
    retry_before = now - OUTBOX_DISPATCH_RETRY_AFTER
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(
                processing_state=OutboxEvent.ProcessingState.PENDING.value,
                event_type=CORRECTION_PUBLICATION_EVENT,
            )
            .filter(
                Q(last_dispatch_attempt_at__isnull=True)
                | Q(last_dispatch_attempt_at__lte=retry_before)
            )
            .order_by("published_at", "id")[:limit]
        )
        for event in events:
            event.dispatch_attempts += 1
            event.last_dispatch_attempt_at = now
            event.save(update_fields=("dispatch_attempts", "last_dispatch_attempt_at"))

    from .tasks import recompute_published_correction

    dispatched = 0
    for event in events:
        try:
            recompute_published_correction.delay(  # pyright: ignore[reportCallIssue]
                event.event_key
            )
        except Exception:
            # The lease expires so beat can retry after a broker outage or worker crash.
            continue
        dispatched += 1
    return dispatched


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

    predecessor_event_key = event.payload.get("predecessor_event_key")
    if predecessor_event_key is not None:
        if not isinstance(predecessor_event_key, str):
            raise CorrectionWorkflowError(
                "Outbox payload field 'predecessor_event_key' must be a string or null."
            )
        process_recomputation_event(event_key=predecessor_event_key)

    execution = JobExecution.objects.create(
        event_key=event.event_key,
        handler_name=RECOMPUTATION_HANDLER,
        status=JobExecution.Status.RUNNING.value,
        started_at=timezone.now(),
    )
    publication_event_id = _payload_int(event.payload, "publication_event_id")
    superseded_claim_id = _payload_int(event.payload, "superseded_claim_id")
    publication = PublicationEvent.objects.get(pk=publication_event_id)
    superseded_claim = EvidenceClaimRevision.objects.get(pk=superseded_claim_id)
    lineage_claim_ids = EvidenceClaimRevision.objects.filter(
        claim_key=superseded_claim.claim_key
    ).values_list("pk", flat=True)
    rule_sets_by_offering = _payload_rule_sets_by_offering(event.payload)
    affected_runs = list(
        ComparisonRun.objects.filter(
            results__assessment_usages__assessment__rule_set__rules__evidence_usages__claim_id__in=(
                lineage_claim_ids
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
            rule_sets_by_offering=rule_sets_by_offering,
        )
        if not created:
            continue
        created_results += 1
        snapshots = DecisionSnapshot.objects.filter(comparison_result__run=run).order_by(
            "created_at", "id"
        )
        for snapshot in snapshots:
            pinned_result = snapshot.comparison_result
            update, update_created = SnapshotUpdate.objects.get_or_create(
                outbox_event=event,
                old_snapshot=snapshot,
                defaults={
                    "old_result": pinned_result,
                    "new_result": new_result,
                    "diff": _comparison_diff(pinned_result, new_result),
                },
            )
            recipient = run.owner
            if recipient is None and run.guest_session is not None:
                recipient = run.guest_session.owner
            notification, notification_created = SnapshotUpdateNotification.objects.get_or_create(
                snapshot_update=update,
                defaults={"recipient": recipient},
            )
            if notification_created:
                AuditEvent.objects.create(
                    actor=None,
                    action="snapshot_update.notification_created",
                    target_type="snapshot_update_notification",
                    target_id=str(notification.pk),
                    metadata={
                        "snapshot_id": str(snapshot.pk),
                        "snapshot_update_id": update.pk,
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
    AuditEvent.objects.create(
        actor=None,
        action="correction.recomputation_succeeded",
        target_type="outbox_event",
        target_id=str(event.pk),
        metadata={**result, "completed_at": completed_at.isoformat()},
    )
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


def _current_rule_set_ids_by_offering() -> dict[str, int | None]:
    rule_set_ids: dict[str, int | None] = {}
    for offering_id in sorted(ENGINEERING_SLICE_OFFERING_IDS):
        rule_set = (
            RuleSetRevision.objects.filter(
                manifest__key=PILOT_MANIFEST_KEY,
                manifest__entries__offering_id=offering_id,
                rules__evidence_usages__claim__offering_id=offering_id,
                namespace=RuleSetRevision.Namespace.PRODUCTION.value,
                target_year=2027,
                status=RuleSetRevision.Status.PUBLISHED.value,
            )
            .distinct()
            .order_by("-revision", "-id")
            .first()
        )
        rule_set_ids[offering_id] = rule_set.pk if rule_set is not None else None
    return rule_set_ids


def _payload_rule_sets_by_offering(
    payload: dict[str, object],
) -> dict[str, RuleSetRevision | None]:
    raw_mapping = payload.get("rule_set_ids_by_offering")
    if not isinstance(raw_mapping, dict):
        raise CorrectionWorkflowError(
            "Outbox payload field 'rule_set_ids_by_offering' must be an object."
        )
    mapping = cast(dict[object, object], raw_mapping)
    expected_ids = set(ENGINEERING_SLICE_OFFERING_IDS)
    if set(mapping) != expected_ids:
        raise CorrectionWorkflowError("Outbox rule-set state must cover the frozen pilot.")
    rule_set_ids = {value for value in mapping.values() if isinstance(value, int)}
    if any(value is not None and not isinstance(value, int) for value in mapping.values()):
        raise CorrectionWorkflowError("Outbox rule-set ids must be integers or null.")
    persisted = RuleSetRevision.objects.in_bulk(rule_set_ids)
    if set(persisted) != rule_set_ids:
        raise CorrectionWorkflowError("An outbox rule-set revision no longer exists.")
    return {
        offering_id: persisted[value] if isinstance(value, int) else None
        for offering_id, value in cast(dict[str, object], mapping).items()
    }


def _require_role(actor: User, role: str) -> None:
    persisted = User.objects.filter(pk=actor.pk).first()
    if persisted is None or not has_staff_role(persisted, role):
        raise CorrectionWorkflowError(
            f"Only a staff member with the {role} role may change correction status."
        )


def _require_assigned_review(case: CorrectionCase, reviewer: User) -> None:
    if (
        case.status != CorrectionCase.Status.REVIEWING.value
        or case.reviewer is None
        or case.reviewer.pk != reviewer.pk
    ):
        raise CorrectionWorkflowError(
            "Only the assigned reviewer may decide a correction under review."
        )
