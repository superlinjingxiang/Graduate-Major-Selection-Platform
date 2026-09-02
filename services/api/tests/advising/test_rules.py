from __future__ import annotations

import pytest
from django.utils import timezone

from gradmatch.advising.models import (
    EligibilityRule,
    PublishedRevisionImmutableError,
    RuleEvidenceUsage,
    RuleSetRevision,
    SourceDocumentRevision,
)
from gradmatch.advising.publication import publish_claim, publish_rule_set
from gradmatch.advising.rules import evaluate_rule

from .factories import (
    approve_claim,
    create_claim,
    create_reviewer,
    create_rule_set,
    create_rule_with_evidence,
    create_source_document,
)


@pytest.mark.django_db
def test_reviewed_2027_evidence_can_publish_a_production_rule_set() -> None:
    reviewer = create_reviewer()
    claim = create_claim(create_source_document(reference_year=2027))
    approve_claim(claim, reviewer)
    claim_event = publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())
    rule_set = create_rule_set(namespace=RuleSetRevision.Namespace.PRODUCTION)
    rule = create_rule_with_evidence(rule_set, claim)

    published = publish_rule_set(
        rule_set_id=rule_set.pk,
        reviewer=reviewer,
        now=timezone.now(),
    )

    assert published.status == RuleSetRevision.Status.PUBLISHED
    assert published.published_at is not None
    assert RuleEvidenceUsage.objects.get(rule=rule).claim == claim_event.claim

    rule.expected_value = False
    with pytest.raises(PublishedRevisionImmutableError, match="published rule set"):
        rule.save()


@pytest.mark.django_db
def test_synthetic_2026_rule_set_can_publish_only_in_fixture_namespace() -> None:
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

    published = publish_rule_set(
        rule_set_id=rule_set.pk,
        reviewer=reviewer,
        now=timezone.now(),
    )

    assert published.status == RuleSetRevision.Status.PUBLISHED
    assert published.namespace == RuleSetRevision.Namespace.TEST_FIXTURE
    assert published.reference_year == 2026


@pytest.mark.parametrize(
    ("operator", "expected", "facts", "outcome"),
    [
        (EligibilityRule.Operator.EQUALS.value, "computer", {"subject": "computer"}, True),
        (
            EligibilityRule.Operator.EQUALS.value,
            "computer",
            {"subject": "mathematics"},
            False,
        ),
        (EligibilityRule.Operator.IN.value, ["A", "B"], {"category": "B"}, True),
        (EligibilityRule.Operator.GTE.value, 80, {"score": 81}, True),
        (EligibilityRule.Operator.GTE.value, 80, {"score": 79}, False),
        (EligibilityRule.Operator.IS_TRUE.value, True, {"confirmed": True}, True),
        (EligibilityRule.Operator.IS_TRUE.value, True, {"confirmed": False}, False),
        (EligibilityRule.Operator.EQUALS.value, "computer", {}, None),
    ],
)
@pytest.mark.django_db
def test_rules_evaluate_deterministically(
    operator: str,
    expected: object,
    facts: dict[str, object],
    outcome: bool | None,
) -> None:
    reviewer = create_reviewer()
    claim = create_claim(create_source_document())
    approve_claim(claim, reviewer)
    publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())
    rule_set = create_rule_set()
    rule = create_rule_with_evidence(
        rule_set,
        claim,
        operator=operator,
        expected_value=expected,
    )
    if "sample_fact" not in facts and facts:
        only_value = next(iter(facts.values()))
        facts = {"sample_fact": only_value}

    assert evaluate_rule(rule, facts) is outcome
