from __future__ import annotations

import json
from typing import cast

import pytest

from gradmatch.advising.comparison import create_comparison_run
from gradmatch.advising.eligibility import canonical_facts_hash
from gradmatch.advising.models import (
    ComparisonAssessmentUsage,
    FactSet,
    FactSetRevision,
    PublishedRevisionImmutableError,
)
from gradmatch.catalog.seed import ENGINEERING_SLICE_OFFERING_IDS

from .factories import create_reviewer

EXPECTED_ENGINEERING_ORDER = [
    "ao_2027_bupt_081200_ft_unified_plan01",
    "ao_2027_bit_085404_ft_unified_plan01",
    "ao_2027_bjut_085410_ft_unified_plan01",
]


def create_fact_revision() -> FactSetRevision:
    facts = {
        "target_year": 2027,
        "region": "北京",
        "study_mode": "full_time",
        "admission_pathway": "unified_exam",
    }
    return FactSetRevision.objects.create(
        fact_set=FactSet.objects.create(owner=create_reviewer()),
        version=1,
        confirmed_facts=facts,
        input_hash=canonical_facts_hash(facts),
    )


@pytest.mark.django_db
def test_current_pilot_comparison_is_deterministic_and_defers_all_offerings() -> None:
    fact_revision = create_fact_revision()

    first = create_comparison_run(
        fact_revision=fact_revision,
        offering_ids=ENGINEERING_SLICE_OFFERING_IDS,
        owner=fact_revision.fact_set.owner,
    )
    second = create_comparison_run(
        fact_revision=fact_revision,
        offering_ids=reversed(EXPECTED_ENGINEERING_ORDER),
        owner=fact_revision.fact_set.owner,
    )

    assert first.result["order"] == EXPECTED_ENGINEERING_ORDER
    assert first.result["groups"] == {
        "eligible_known": [],
        "ineligible_known": [],
        "needs_confirmation": EXPECTED_ENGINEERING_ORDER,
    }
    assessments = cast(list[dict[str, object]], first.result["assessments"])
    assert [item["status"] for item in assessments] == [
        "needs_confirmation",
        "needs_confirmation",
        "needs_confirmation",
    ]
    assert first.result_hash == second.result_hash
    assert first.run.pk != second.run.pk
    assert list(
        ComparisonAssessmentUsage.objects.filter(result=first)
        .order_by("position")
        .values_list("assessment__offering_id", flat=True)
    ) == EXPECTED_ENGINEERING_ORDER

    first.run.selected_offering_ids = []
    with pytest.raises(PublishedRevisionImmutableError, match="comparison run"):
        first.run.save()
    serialized = json.dumps(first.result)
    assert "probability" not in serialized
    assert "confidence" not in serialized
    assert "score" not in serialized
    assert "rank" not in serialized


@pytest.mark.django_db
def test_comparison_rejects_an_offering_outside_the_engineering_slice() -> None:
    fact_revision = create_fact_revision()

    with pytest.raises(ValueError, match="engineering slice"):
        create_comparison_run(
            fact_revision=fact_revision,
            offering_ids=["ao_2027_bupt_085404_ft_unified_plan01"],
            owner=fact_revision.fact_set.owner,
        )
