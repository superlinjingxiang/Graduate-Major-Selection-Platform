from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import cast

from django.db import transaction

from gradmatch.accounts.models import User
from gradmatch.catalog.models import ManifestEntry
from gradmatch.catalog.seed import ENGINEERING_SLICE_OFFERING_IDS, PILOT_MANIFEST_KEY

from .eligibility import assess_eligibility
from .models import (
    ComparisonAssessmentUsage,
    ComparisonRun,
    ComparisonRunResult,
    DecisionSnapshot,
    FactSetRevision,
    GuestSession,
)


@transaction.atomic
def create_comparison_run(
    *,
    fact_revision: FactSetRevision,
    offering_ids: Iterable[str] = ENGINEERING_SLICE_OFFERING_IDS,
    owner: User | None = None,
    guest_session: GuestSession | None = None,
) -> ComparisonRunResult:
    requested_ids = set(offering_ids)
    if not requested_ids or not requested_ids.issubset(ENGINEERING_SLICE_OFFERING_IDS):
        raise ValueError("Comparison offerings must stay inside the frozen engineering slice.")
    if (owner is None) == (guest_session is None):
        raise ValueError("A comparison requires exactly one account or guest owner.")

    entries = list(
        ManifestEntry.objects.filter(
            manifest__key=PILOT_MANIFEST_KEY,
            engineering_slice=True,
            offering__pk__in=requested_ids,
        )
        .select_related("manifest", "offering")
        .order_by("position")
    )
    ordered_offerings = [entry.offering for entry in entries]
    if {offering.pk for offering in ordered_offerings} != requested_ids:
        raise ValueError("One or more offerings are outside the frozen engineering slice.")

    assessments = [
        assess_eligibility(offering=offering, fact_revision=fact_revision)
        for offering in ordered_offerings
    ]
    groups: dict[str, list[str]] = {
        "eligible_known": [],
        "ineligible_known": [],
        "needs_confirmation": [],
    }
    serialized_assessments: list[dict[str, object]] = []
    for assessment in assessments:
        groups[assessment.status].append(assessment.offering.pk)
        serialized_assessments.append(
            {
                "offering_id": assessment.offering.pk,
                "assessment_id": assessment.pk,
                "status": assessment.status,
                "reasons": assessment.reasons,
                "input_hash": assessment.input_hash,
            }
        )

    result: dict[str, object] = {
        "manifest_key": entries[0].manifest.key,
        "order": [offering.pk for offering in ordered_offerings],
        "groups": groups,
        "assessments": serialized_assessments,
    }
    result_hash = _canonical_hash(_semantic_result(result))
    run = ComparisonRun.objects.create(
        fact_revision=fact_revision,
        manifest=entries[0].manifest,
        selected_offering_ids=result["order"],
        owner=owner,
        guest_session=guest_session,
    )
    comparison_result = ComparisonRunResult.objects.create(
        run=run,
        version=1,
        result=result,
        result_hash=result_hash,
    )
    ComparisonAssessmentUsage.objects.bulk_create(
        [
            ComparisonAssessmentUsage(
                result=comparison_result,
                assessment=assessment,
                position=position,
            )
            for position, assessment in enumerate(assessments, start=1)
        ]
    )
    return comparison_result


@transaction.atomic
def create_decision_snapshot(
    *,
    comparison_result: ComparisonRunResult,
    requested_outcome: str | None = None,
) -> DecisionSnapshot:
    groups = _result_groups(comparison_result.result)
    inferred_outcome = _infer_outcome(groups)
    if requested_outcome is None:
        outcome = inferred_outcome
    elif requested_outcome == DecisionSnapshot.Outcome.POSTPONE_APPLICATION.value:
        outcome = requested_outcome
    elif requested_outcome == inferred_outcome:
        outcome = requested_outcome
    else:
        raise ValueError("The requested outcome conflicts with the deterministic comparison.")

    key_unknowns = _unknown_reason_codes(comparison_result.result)
    next_actions = [
        action
        for code in key_unknowns
        if (action := _action_for_reason(code)) is not None
    ]
    snapshot_payload: dict[str, object] = {
        "comparison_result_hash": comparison_result.result_hash,
        "outcome": outcome,
        "retained": groups["eligible_known"],
        "excluded": groups["ineligible_known"],
        "deferred": groups["needs_confirmation"],
        "user_confirmed_reasons": [],
        "key_unknowns": key_unknowns,
        "next_actions": next_actions,
        "revisit_date": None,
    }
    return DecisionSnapshot.objects.create(
        comparison_result=comparison_result,
        outcome=outcome,
        retained=groups["eligible_known"],
        excluded=groups["ineligible_known"],
        deferred=groups["needs_confirmation"],
        user_confirmed_reasons=[],
        key_unknowns=key_unknowns,
        next_actions=next_actions,
        revisit_date=None,
        snapshot_hash=_canonical_hash(snapshot_payload),
    )


def latest_comparison_result(run: ComparisonRun) -> ComparisonRunResult:
    result = ComparisonRunResult.objects.filter(run=run).order_by("-version").first()
    if result is None:
        raise ComparisonRunResult.DoesNotExist("Comparison run has no result revision.")
    return result


def _infer_outcome(groups: dict[str, list[str]]) -> str:
    if groups["eligible_known"]:
        return DecisionSnapshot.Outcome.SHORTLIST_READY.value
    if groups["needs_confirmation"]:
        return DecisionSnapshot.Outcome.AWAITING_OFFICIAL_INFORMATION.value
    return DecisionSnapshot.Outcome.NO_SUITABLE_OFFERING.value


def _result_groups(result: dict[str, object]) -> dict[str, list[str]]:
    raw_groups = result.get("groups")
    if not isinstance(raw_groups, dict):
        raise ValueError("Comparison result groups are invalid.")
    groups = cast(dict[str, object], raw_groups)
    normalized: dict[str, list[str]] = {}
    for key in ("eligible_known", "ineligible_known", "needs_confirmation"):
        values = groups.get(key)
        if not isinstance(values, list):
            raise ValueError("Comparison result group values are invalid.")
        group_values = cast(list[object], values)
        if not all(isinstance(item, str) for item in group_values):
            raise ValueError("Comparison result group values are invalid.")
        normalized[key] = cast(list[str], group_values)
    return normalized


def _unknown_reason_codes(result: dict[str, object]) -> list[str]:
    assessments = result.get("assessments")
    if not isinstance(assessments, list):
        raise ValueError("Comparison assessments are invalid.")
    codes: list[str] = []
    for raw_assessment in cast(list[object], assessments):
        if not isinstance(raw_assessment, dict):
            raise ValueError("Comparison assessment is invalid.")
        assessment = cast(dict[str, object], raw_assessment)
        if assessment.get("status") != "needs_confirmation":
            continue
        reasons = assessment.get("reasons")
        if not isinstance(reasons, list):
            raise ValueError("Comparison assessment reasons are invalid.")
        for raw_reason in cast(list[object], reasons):
            if not isinstance(raw_reason, dict):
                raise ValueError("Comparison reason is invalid.")
            code = cast(dict[str, object], raw_reason).get("code")
            if isinstance(code, str) and code not in codes:
                codes.append(code)
    return codes


def _action_for_reason(code: str) -> str | None:
    if code in {"rule_unpublished", "rule_set_incomplete"}:
        return "等待并复核 2027 官方招生信息"
    if code == "user_fact_missing":
        return "补充并确认影响报考资格的个人事实"
    return None


def _canonical_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _semantic_result(result: dict[str, object]) -> dict[str, object]:
    semantic = dict(result)
    raw_assessments = result.get("assessments")
    if not isinstance(raw_assessments, list):
        raise ValueError("Comparison assessments are invalid.")
    semantic_assessments: list[dict[str, object]] = []
    for raw_assessment in cast(list[object], raw_assessments):
        if not isinstance(raw_assessment, dict):
            raise ValueError("Comparison assessment is invalid.")
        assessment = dict(cast(dict[str, object], raw_assessment))
        assessment.pop("assessment_id", None)
        semantic_assessments.append(assessment)
    semantic["assessments"] = semantic_assessments
    return semantic
