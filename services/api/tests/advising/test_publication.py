from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from gradmatch.advising.models import (
    EligibilityRule,
    EvidenceClaimRevision,
    PublishedRevisionImmutableError,
    ReviewDecision,
    RuleEvidenceUsage,
    RuleSetRevision,
    SourceDocumentRevision,
)
from gradmatch.advising.publication import (
    EvidencePublicationError,
    FixtureIsolationError,
    publish_claim,
    publish_rule_set,
    revise_claim,
)
from gradmatch.catalog.models import AnnualOffering

from .factories import (
    approve_claim,
    create_claim,
    create_reviewer,
    create_rule_set,
    create_rule_with_evidence,
    create_source_document,
)


@pytest.mark.django_db
def test_unreviewed_claim_cannot_be_published() -> None:
    reviewer = create_reviewer()
    claim = create_claim(create_source_document())

    with pytest.raises(EvidencePublicationError, match="approved review"):
        publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())


@pytest.mark.django_db
def test_latest_review_decision_must_be_approved() -> None:
    reviewer = create_reviewer()
    claim = create_claim(create_source_document())
    approve_claim(claim, reviewer)
    ReviewDecision.objects.create(
        claim=claim,
        reviewer=reviewer,
        outcome=ReviewDecision.Outcome.REJECTED,
        note="A later review found the source insufficient.",
    )

    with pytest.raises(EvidencePublicationError, match="latest review"):
        publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())


@pytest.mark.django_db
def test_synthetic_evidence_cannot_enter_a_production_rule_set() -> None:
    reviewer = create_reviewer()
    source = create_source_document(
        data_class=SourceDocumentRevision.DataClass.SYNTHETIC,
        reference_year=2026,
    )
    claim = create_claim(source)
    approve_claim(claim, reviewer)
    publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())
    rule_set = create_rule_set(namespace=RuleSetRevision.Namespace.PRODUCTION)
    create_rule_with_evidence(rule_set, claim)

    with pytest.raises(FixtureIsolationError, match="production"):
        publish_rule_set(rule_set_id=rule_set.pk, reviewer=reviewer, now=timezone.now())


@pytest.mark.django_db
def test_reference_year_cannot_be_attached_to_a_production_rule_set() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        create_rule_set(
            namespace=RuleSetRevision.Namespace.PRODUCTION,
            reference_year=2026,
        )


@pytest.mark.django_db
def test_production_rule_requires_published_current_year_evidence() -> None:
    reviewer = create_reviewer()
    claim = create_claim(create_source_document(reference_year=2027))
    approve_claim(claim, reviewer)
    rule_set = create_rule_set()
    create_rule_with_evidence(rule_set, claim)

    with pytest.raises(EvidencePublicationError, match="published claim"):
        publish_rule_set(rule_set_id=rule_set.pk, reviewer=reviewer, now=timezone.now())


@pytest.mark.django_db
def test_rule_set_cannot_mix_evidence_from_different_offerings() -> None:
    reviewer = create_reviewer()
    first_claim = create_claim(create_source_document())
    second_claim = create_claim(
        create_source_document(),
        offering=AnnualOffering.objects.get(pk="ao_2027_bit_085404_ft_unified_plan01"),
    )
    for claim in (first_claim, second_claim):
        approve_claim(claim, reviewer)
        publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())

    rule_set = create_rule_set()
    create_rule_with_evidence(rule_set, first_claim)
    second_rule = EligibilityRule.objects.create(
        rule_set=rule_set,
        key="second-offering-rule",
        position=2,
        fact_key="second_fact",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=True,
        failure_reason_code="second_rule_failed",
    )
    RuleEvidenceUsage.objects.create(rule=second_rule, claim=second_claim)

    with pytest.raises(EvidencePublicationError, match="one offering"):
        publish_rule_set(rule_set_id=rule_set.pk, reviewer=reviewer, now=timezone.now())


@pytest.mark.django_db
def test_published_claim_is_append_only_and_corrections_create_a_revision() -> None:
    reviewer = create_reviewer()
    claim = create_claim(create_source_document(), normalized_value=True)
    approve_claim(claim, reviewer)
    event = publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())

    claim.normalized_value = False
    with pytest.raises(PublishedRevisionImmutableError, match="published"):
        claim.save()

    replacement_source = create_source_document()
    replacement = revise_claim(
        claim_id=claim.pk,
        source_document=replacement_source,
        normalized_value=False,
        original_value="false",
    )

    claim.refresh_from_db()
    assert event.claim == claim
    assert claim.revision == 1
    assert claim.normalized_value is True
    assert replacement.claim_key == claim.claim_key
    assert replacement.revision == 2
    assert replacement.supersedes == claim
    assert replacement.normalized_value is False
    assert EvidenceClaimRevision.objects.filter(claim_key=claim.claim_key).count() == 2

    source = claim.source_document
    source.reference_year = 2026
    with pytest.raises(PublishedRevisionImmutableError, match="source document"):
        source.save()
