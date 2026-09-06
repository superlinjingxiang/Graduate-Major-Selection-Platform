from __future__ import annotations

from collections.abc import Mapping

import pytest
from django.utils import timezone

from gradmatch.advising.eligibility import assess_eligibility, canonical_facts_hash
from gradmatch.advising.models import (
    EligibilityAssessment,
    FactSet,
    FactSetRevision,
    PublishedRevisionImmutableError,
    RuleSetRevision,
    SourceDocumentRevision,
)
from gradmatch.advising.publication import FixtureIsolationError, publish_claim, publish_rule_set
from gradmatch.catalog.models import AnnualOffering, CoverageManifest, ManifestEntry
from gradmatch.catalog.seed import ENGINEERING_SLICE_OFFERING_IDS

from .factories import (
    approve_claim,
    create_claim,
    create_reviewer,
    create_rule_set,
    create_rule_with_evidence,
    create_source_document,
)


def create_fact_revision(facts: Mapping[str, object]) -> FactSetRevision:
    fact_set = FactSet.objects.create()
    return FactSetRevision.objects.create(
        fact_set=fact_set,
        version=1,
        confirmed_facts=dict(facts),
        input_hash=canonical_facts_hash(facts),
    )


@pytest.mark.django_db
def test_current_engineering_slice_requires_confirmation_until_rules_publish() -> None:
    facts = create_fact_revision(
        {
            "target_year": 2027,
            "region": "北京",
            "study_mode": "full_time",
            "admission_pathway": "unified_exam",
        }
    )

    assessments = [
        assess_eligibility(
            offering=AnnualOffering.objects.get(pk=offering_id),
            fact_revision=facts,
        )
        for offering_id in sorted(ENGINEERING_SLICE_OFFERING_IDS)
    ]

    assert [item.status for item in assessments] == [
        EligibilityAssessment.Status.NEEDS_CONFIRMATION.value,
        EligibilityAssessment.Status.NEEDS_CONFIRMATION.value,
        EligibilityAssessment.Status.NEEDS_CONFIRMATION.value,
    ]
    assert [item.reasons for item in assessments] == [
        [{"code": "rule_unpublished", "fact_key": None, "rule_key": None}],
        [{"code": "rule_unpublished", "fact_key": None, "rule_key": None}],
        [{"code": "rule_unpublished", "fact_key": None, "rule_key": None}],
    ]
    assert all(item.rule_set is None for item in assessments)


@pytest.mark.django_db
def test_rules_from_another_manifest_cannot_drive_pilot_eligibility() -> None:
    reviewer = create_reviewer()
    offering = AnnualOffering.objects.get(pk="ao_2027_bupt_081200_ft_unified_plan01")
    alternate_manifest = CoverageManifest.objects.create(
        key="alternate-2027-manifest",
        version=1,
        target_year=2027,
        scope={"purpose": "regression-test"},
        frozen_at=timezone.now(),
    )
    ManifestEntry.objects.create(
        manifest=alternate_manifest,
        offering=offering,
        position=1,
    )
    claim = create_claim(create_source_document(), offering=offering)
    approve_claim(claim, reviewer)
    publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())
    rule_set = RuleSetRevision.objects.create(
        key="alternate-manifest-rules",
        revision=1,
        namespace=RuleSetRevision.Namespace.PRODUCTION,
        target_year=2027,
        manifest=alternate_manifest,
        coverage_complete=True,
    )
    create_rule_with_evidence(rule_set, claim)
    publish_rule_set(rule_set_id=rule_set.pk, reviewer=reviewer, now=timezone.now())

    assessment = assess_eligibility(
        offering=offering,
        fact_revision=create_fact_revision({"sample_fact": True}),
    )

    assert assessment.status == EligibilityAssessment.Status.NEEDS_CONFIRMATION.value
    assert assessment.rule_set is None
    assert assessment.reasons == [
        {"code": "rule_unpublished", "fact_key": None, "rule_key": None}
    ]


@pytest.mark.django_db
def test_fixture_rules_cover_all_three_eligibility_states_without_api_access() -> None:
    reviewer = create_reviewer()
    source = create_source_document(
        data_class=SourceDocumentRevision.DataClass.SYNTHETIC,
        reference_year=2026,
    )
    claim = create_claim(source)
    approve_claim(claim, reviewer)
    publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())
    rule_set = create_rule_set(
        namespace=RuleSetRevision.Namespace.TEST_FIXTURE,
        reference_year=2026,
    )
    create_rule_with_evidence(rule_set, claim)
    publish_rule_set(rule_set_id=rule_set.pk, reviewer=reviewer, now=timezone.now())
    offering = claim.offering

    eligible = assess_eligibility(
        offering=offering,
        fact_revision=create_fact_revision({"sample_fact": True}),
        rule_set=rule_set,
        allow_test_fixture=True,
    )
    ineligible = assess_eligibility(
        offering=offering,
        fact_revision=create_fact_revision({"sample_fact": False}),
        rule_set=rule_set,
        allow_test_fixture=True,
    )
    unknown = assess_eligibility(
        offering=offering,
        fact_revision=create_fact_revision({}),
        rule_set=rule_set,
        allow_test_fixture=True,
    )

    assert eligible.status == EligibilityAssessment.Status.ELIGIBLE_KNOWN.value
    assert eligible.reasons == []
    assert ineligible.status == EligibilityAssessment.Status.INELIGIBLE_KNOWN.value
    assert ineligible.reasons == [
        {
            "code": "sample_rule_failed",
            "fact_key": "sample_fact",
            "rule_key": "sample-rule",
        }
    ]
    assert unknown.status == EligibilityAssessment.Status.NEEDS_CONFIRMATION.value
    assert unknown.reasons == [
        {
            "code": "user_fact_missing",
            "fact_key": "sample_fact",
            "rule_key": "sample-rule",
        }
    ]


@pytest.mark.django_db
def test_fixture_rule_set_requires_an_explicit_service_only_switch() -> None:
    rule_set = create_rule_set(
        namespace=RuleSetRevision.Namespace.TEST_FIXTURE,
        reference_year=2026,
    )

    with pytest.raises(FixtureIsolationError, match="explicitly enabled"):
        assess_eligibility(
            offering=AnnualOffering.objects.get(
                pk="ao_2027_bupt_081200_ft_unified_plan01"
            ),
            fact_revision=create_fact_revision({"sample_fact": True}),
            rule_set=rule_set,
        )


@pytest.mark.django_db
def test_published_but_incomplete_rule_set_requires_confirmation() -> None:
    reviewer = create_reviewer()
    source = create_source_document(
        data_class=SourceDocumentRevision.DataClass.SYNTHETIC,
        reference_year=2026,
    )
    claim = create_claim(source)
    approve_claim(claim, reviewer)
    publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())
    rule_set = create_rule_set(
        namespace=RuleSetRevision.Namespace.TEST_FIXTURE,
        reference_year=2026,
        coverage_complete=False,
    )
    create_rule_with_evidence(rule_set, claim)
    publish_rule_set(rule_set_id=rule_set.pk, reviewer=reviewer, now=timezone.now())

    assessment = assess_eligibility(
        offering=claim.offering,
        fact_revision=create_fact_revision({"sample_fact": True}),
        rule_set=rule_set,
        allow_test_fixture=True,
    )

    assert assessment.status == EligibilityAssessment.Status.NEEDS_CONFIRMATION.value
    assert assessment.reasons == [
        {"code": "rule_set_incomplete", "fact_key": None, "rule_key": None}
    ]


@pytest.mark.django_db
def test_identical_canonical_inputs_have_identical_hashes_and_reason_order() -> None:
    first_facts = {"region": "北京", "target_year": 2027}
    second_facts = {"target_year": 2027, "region": "北京"}
    offering = AnnualOffering.objects.get(pk="ao_2027_bupt_081200_ft_unified_plan01")

    first = assess_eligibility(
        offering=offering,
        fact_revision=create_fact_revision(first_facts),
    )
    second = assess_eligibility(
        offering=offering,
        fact_revision=create_fact_revision(second_facts),
    )

    assert canonical_facts_hash(first_facts) == canonical_facts_hash(second_facts)
    assert first.input_hash == second.input_hash
    assert first.reasons == second.reasons
    assert first.pk != second.pk


@pytest.mark.django_db
def test_fact_set_revision_is_immutable_after_creation() -> None:
    revision = create_fact_revision({"target_year": 2027})

    revision.confirmed_facts = {"target_year": 2028}
    with pytest.raises(PublishedRevisionImmutableError, match="fact set revision"):
        revision.save()
