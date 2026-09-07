from __future__ import annotations

from datetime import datetime

from django.db import transaction

from gradmatch.accounts.models import User
from gradmatch.accounts.roles import (
    ADMINISTRATOR_ROLE,
    EDITOR_ROLE,
    REVIEWER_ROLE,
    has_staff_role,
)
from gradmatch.catalog.models import ManifestEntry

from .models import (
    EligibilityRule,
    EvidenceClaimRevision,
    PublicationEvent,
    ReviewDecision,
    RuleEvidenceUsage,
    RuleSetRevision,
    SourceDocumentRevision,
)


class EvidencePublicationError(RuntimeError):
    pass


class FixtureIsolationError(EvidencePublicationError):
    pass


@transaction.atomic
def publish_claim(
    *,
    claim_id: int,
    reviewer: User,
    now: datetime,
) -> PublicationEvent:
    _require_role(reviewer, ADMINISTRATOR_ROLE)
    claim = EvidenceClaimRevision.objects.select_for_update().get(pk=claim_id)
    latest_review = (
        ReviewDecision.objects.filter(claim=claim).order_by("-created_at", "-id").first()
    )
    if latest_review is None:
        raise EvidencePublicationError("A claim requires an approved review before publication.")
    if latest_review.outcome != ReviewDecision.Outcome.APPROVED.value:
        raise EvidencePublicationError("The latest review decision must be approved.")
    if not has_staff_role(latest_review.reviewer, REVIEWER_ROLE):
        raise EvidencePublicationError("The latest decision requires the reviewer role.")
    if claim.created_by is None or latest_review.reviewer.pk == claim.created_by.pk:
        raise EvidencePublicationError("A claim requires an independent reviewer.")
    if not has_staff_role(claim.created_by, EDITOR_ROLE):
        raise EvidencePublicationError("A claim requires a creator with the editor role.")
    event, _ = PublicationEvent.objects.get_or_create(
        claim=claim,
        defaults={"reviewer": reviewer, "published_at": now},
    )
    return event


@transaction.atomic
def publish_rule_set(
    *,
    rule_set_id: int,
    reviewer: User,
    now: datetime,
) -> RuleSetRevision:
    _require_role(reviewer, ADMINISTRATOR_ROLE)
    rule_set = RuleSetRevision.objects.select_for_update().get(pk=rule_set_id)
    if rule_set.status == RuleSetRevision.Status.PUBLISHED.value:
        return rule_set
    if rule_set.created_by is None or rule_set.created_by.pk == reviewer.pk:
        raise EvidencePublicationError("A rule set requires publication by a separate actor.")
    if not has_staff_role(rule_set.created_by, EDITOR_ROLE):
        raise EvidencePublicationError("A rule set requires a creator with the editor role.")

    rules = list(EligibilityRule.objects.filter(rule_set=rule_set).order_by("position"))
    if not rules:
        raise EvidencePublicationError("A rule set requires at least one evidence-backed rule.")
    evidence_offering_ids: set[str] = set()
    for rule in rules:
        usages = list(
            RuleEvidenceUsage.objects.filter(rule=rule).select_related(
                "claim__source_document",
                "claim__offering",
            )
        )
        if not usages:
            raise EvidencePublicationError(f"Rule '{rule.key}' requires a published claim.")
        for usage in usages:
            claim = usage.claim
            evidence_offering_ids.add(claim.offering.pk)
            if not PublicationEvent.objects.filter(claim=claim).exists():
                raise EvidencePublicationError(f"Rule '{rule.key}' requires a published claim.")
            if not ManifestEntry.objects.filter(
                manifest=rule_set.manifest,
                offering=claim.offering,
            ).exists():
                raise EvidencePublicationError("Rule evidence must belong to the frozen manifest.")
            _validate_evidence_namespace(rule_set, claim)

    if len(evidence_offering_ids) != 1:
        raise EvidencePublicationError("A rule set must contain evidence for exactly one offering.")

    rule_set.status = RuleSetRevision.Status.PUBLISHED.value
    rule_set.published_at = now
    rule_set.published_by = reviewer
    rule_set.save(update_fields=("status", "published_at", "published_by"))
    return rule_set


@transaction.atomic
def revise_claim(
    *,
    claim_id: int,
    source_document: SourceDocumentRevision,
    normalized_value: object,
    original_value: str,
) -> EvidenceClaimRevision:
    claim = EvidenceClaimRevision.objects.select_for_update().get(pk=claim_id)
    if not PublicationEvent.objects.filter(claim=claim).exists():
        raise EvidencePublicationError("Only a published claim can be revised.")
    if EvidenceClaimRevision.objects.filter(supersedes=claim).exists():
        raise EvidencePublicationError("The claim already has a replacement revision.")
    if source_document.created_by is None or not has_staff_role(
        source_document.created_by, EDITOR_ROLE
    ):
        raise EvidencePublicationError("A revised claim requires a creator with the editor role.")
    return EvidenceClaimRevision.objects.create(
        claim_key=claim.claim_key,
        revision=claim.revision + 1,
        supersedes=claim,
        offering=claim.offering,
        field_key=claim.field_key,
        normalized_value=normalized_value,
        original_value=original_value,
        source_document=source_document,
        created_by=source_document.created_by,
    )


def _validate_evidence_namespace(
    rule_set: RuleSetRevision,
    claim: EvidenceClaimRevision,
) -> None:
    source_document = claim.source_document
    if rule_set.namespace == RuleSetRevision.Namespace.PRODUCTION.value:
        if source_document.data_class != SourceDocumentRevision.DataClass.PRODUCTION.value:
            raise FixtureIsolationError("Synthetic or historical evidence cannot enter production.")
        if source_document.reference_year != rule_set.target_year:
            raise FixtureIsolationError("Production evidence must match the target year.")
        if claim.offering.target_year != rule_set.target_year:
            raise FixtureIsolationError("Production claims must match the target year.")
        return

    if source_document.data_class == SourceDocumentRevision.DataClass.PRODUCTION.value:
        raise FixtureIsolationError("Fixture rule sets require isolated fixture evidence.")
    if source_document.reference_year != rule_set.reference_year:
        raise FixtureIsolationError("Fixture evidence must match its reference year.")


def _require_role(actor: User, role: str) -> None:
    persisted = User.objects.filter(pk=actor.pk).first()
    if persisted is None or not has_staff_role(persisted, role):
        raise EvidencePublicationError(
            f"Only a staff member with the {role} role may perform this publication."
        )
