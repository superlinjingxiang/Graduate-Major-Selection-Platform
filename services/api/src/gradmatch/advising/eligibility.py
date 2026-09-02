from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from gradmatch.catalog.models import AnnualOffering, ManifestEntry
from gradmatch.catalog.seed import PILOT_MANIFEST_KEY

from .models import (
    EligibilityAssessment,
    EligibilityRule,
    FactSetRevision,
    RuleEvidenceUsage,
    RuleSetRevision,
)
from .publication import FixtureIsolationError
from .rules import evaluate_rule

Reason = dict[str, object]


class EligibilityScopeError(ValueError):
    pass


def canonical_facts_hash(facts: Mapping[str, object]) -> str:
    serialized = json.dumps(
        facts,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def assess_eligibility(
    *,
    offering: AnnualOffering,
    fact_revision: FactSetRevision,
    rule_set: RuleSetRevision | None = None,
    allow_test_fixture: bool = False,
) -> EligibilityAssessment:
    manifest_entry = ManifestEntry.objects.filter(
        manifest__key=PILOT_MANIFEST_KEY,
        offering=offering,
    ).select_related("manifest").first()
    if manifest_entry is None:
        raise EligibilityScopeError("The offering is outside the active pilot manifest.")

    active_rule_set = (
        RuleSetRevision.objects.get(pk=rule_set.pk)
        if rule_set is not None
        else _find_production_rule_set(offering)
    )
    if active_rule_set is not None:
        _guard_rule_set_namespace(active_rule_set, allow_test_fixture=allow_test_fixture)

    status, reasons = _calculate_status(active_rule_set, fact_revision.confirmed_facts)
    input_hash = _assessment_hash(
        offering=offering,
        fact_revision=fact_revision,
        rule_set=active_rule_set,
    )
    return EligibilityAssessment.objects.create(
        offering=offering,
        fact_revision=fact_revision,
        rule_set=active_rule_set,
        status=status,
        reasons=reasons,
        input_hash=input_hash,
    )


def _find_production_rule_set(offering: AnnualOffering) -> RuleSetRevision | None:
    return (
        RuleSetRevision.objects.filter(
            manifest__entries__offering=offering,
            namespace=RuleSetRevision.Namespace.PRODUCTION.value,
            target_year=offering.target_year,
            status=RuleSetRevision.Status.PUBLISHED.value,
        )
        .order_by("-revision", "-id")
        .first()
    )


def _guard_rule_set_namespace(
    rule_set: RuleSetRevision,
    *,
    allow_test_fixture: bool,
) -> None:
    is_fixture = rule_set.namespace == RuleSetRevision.Namespace.TEST_FIXTURE.value
    if is_fixture and not allow_test_fixture:
        raise FixtureIsolationError(
            "Test fixture rule sets must be explicitly enabled in services."
        )


def _calculate_status(
    rule_set: RuleSetRevision | None,
    facts: dict[str, object],
) -> tuple[str, list[Reason]]:
    if rule_set is None or rule_set.status != RuleSetRevision.Status.PUBLISHED.value:
        return (
            EligibilityAssessment.Status.NEEDS_CONFIRMATION.value,
            [_reason("rule_unpublished")],
        )
    if not rule_set.coverage_complete:
        return (
            EligibilityAssessment.Status.NEEDS_CONFIRMATION.value,
            [_reason("rule_set_incomplete")],
        )

    rules = list(EligibilityRule.objects.filter(rule_set=rule_set).order_by("position", "id"))
    if not rules:
        return (
            EligibilityAssessment.Status.NEEDS_CONFIRMATION.value,
            [_reason("rule_unpublished")],
        )

    failures: list[Reason] = []
    unknowns: list[Reason] = []
    for rule in rules:
        outcome = evaluate_rule(rule, facts)
        if outcome is False:
            failures.append(_reason(rule.failure_reason_code, rule=rule))
        elif outcome is None:
            unknowns.append(_reason("user_fact_missing", rule=rule))

    if failures:
        return EligibilityAssessment.Status.INELIGIBLE_KNOWN.value, failures
    if unknowns:
        return EligibilityAssessment.Status.NEEDS_CONFIRMATION.value, unknowns
    return EligibilityAssessment.Status.ELIGIBLE_KNOWN.value, []


def _reason(code: str, *, rule: EligibilityRule | None = None) -> Reason:
    if rule is None:
        return {"code": code, "fact_key": None, "rule_key": None}
    return {"code": code, "fact_key": rule.fact_key, "rule_key": rule.key}


def _assessment_hash(
    *,
    offering: AnnualOffering,
    fact_revision: FactSetRevision,
    rule_set: RuleSetRevision | None,
) -> str:
    rule_identity: dict[str, object] | None = None
    if rule_set is not None:
        rule_identity = {
            "key": rule_set.key,
            "revision": rule_set.revision,
            "namespace": rule_set.namespace,
            "evidence_claim_ids": list(
                RuleEvidenceUsage.objects.filter(rule__rule_set=rule_set)
                .order_by("rule__position", "claim_id")
                .values_list("claim_id", flat=True)
            ),
        }
    payload = {
        "offering_id": offering.pk,
        "facts_hash": fact_revision.input_hash,
        "rule_set": rule_identity,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(serialized).hexdigest()
