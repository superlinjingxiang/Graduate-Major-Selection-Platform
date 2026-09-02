from __future__ import annotations

from typing import cast
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError
from pydantic import ConfigDict

from gradmatch.accounts.models import User
from gradmatch.catalog.models import AnnualOffering
from gradmatch.catalog.seed import PILOT_MANIFEST_KEY

from .eligibility import assess_eligibility, canonical_facts_hash
from .models import EligibilityAssessment, FactSet, FactSetRevision

router = Router(tags=["advising"])

ALLOWED_FACT_KEYS = frozenset(
    {
        "age_18_or_over",
        "target_year",
        "region",
        "study_mode",
        "admission_pathway",
        "education_level",
        "undergraduate_major",
        "equivalent_education",
        "cross_discipline",
        "years_of_work_experience",
        "overseas_degree_certified",
        "directed_employment_confirmed",
    }
)


class FactSetCreateRequest(Schema):
    model_config = ConfigDict(extra="forbid")

    confirmed_facts: dict[str, object]


class FactSetResponse(Schema):
    fact_set_id: UUID
    version: int
    confirmed_facts: dict[str, object]
    input_hash: str


class EligibilityAssessmentRequest(Schema):
    model_config = ConfigDict(extra="forbid")

    offering_id: str
    fact_set_id: UUID
    fact_revision: int


class EligibilityAssessmentResponse(Schema):
    assessment_id: int
    offering_id: str
    fact_set_id: UUID
    fact_revision: int
    rule_set_key: str | None
    rule_set_revision: int | None
    status: str
    reasons: list[dict[str, object]]
    input_hash: str


@router.post("/fact-sets", response={201: FactSetResponse}, operation_id="create_fact_set")
def create_fact_set(
    request: HttpRequest,
    payload: FactSetCreateRequest,
) -> Status[FactSetResponse]:
    unknown_keys = sorted(set(payload.confirmed_facts) - ALLOWED_FACT_KEYS)
    if unknown_keys:
        raise HttpError(422, f"Unknown confirmed fact keys: {', '.join(unknown_keys)}")

    request_user = cast(object, getattr(request, "user", None))
    owner = request_user if isinstance(request_user, User) else None
    with transaction.atomic():
        fact_set = FactSet.objects.create(owner=owner)
        revision = FactSetRevision.objects.create(
            fact_set=fact_set,
            version=1,
            confirmed_facts=payload.confirmed_facts,
            input_hash=canonical_facts_hash(payload.confirmed_facts),
        )
    return Status(
        201,
        FactSetResponse(
            fact_set_id=fact_set.pk,
            version=revision.version,
            confirmed_facts=revision.confirmed_facts,
            input_hash=revision.input_hash,
        ),
    )


@router.post(
    "/eligibility-assessments",
    response={201: EligibilityAssessmentResponse},
    operation_id="create_eligibility_assessment",
)
def create_eligibility_assessment(
    request: HttpRequest,
    payload: EligibilityAssessmentRequest,
) -> Status[EligibilityAssessmentResponse]:
    del request
    offering = get_object_or_404(
        AnnualOffering.objects.filter(manifest_entries__manifest__key=PILOT_MANIFEST_KEY),
        pk=payload.offering_id,
    )
    fact_revision = get_object_or_404(
        FactSetRevision.objects.select_related("fact_set"),
        fact_set_id=payload.fact_set_id,
        version=payload.fact_revision,
    )
    assessment = assess_eligibility(
        offering=offering,
        fact_revision=fact_revision,
    )
    return Status(201, _serialize_assessment(assessment))


def _serialize_assessment(assessment: EligibilityAssessment) -> EligibilityAssessmentResponse:
    rule_set = assessment.rule_set
    return EligibilityAssessmentResponse(
        assessment_id=cast(int, assessment.pk),
        offering_id=assessment.offering.pk,
        fact_set_id=assessment.fact_revision.fact_set.pk,
        fact_revision=assessment.fact_revision.version,
        rule_set_key=rule_set.key if rule_set is not None else None,
        rule_set_revision=rule_set.revision if rule_set is not None else None,
        status=assessment.status,
        reasons=assessment.reasons,
        input_hash=assessment.input_hash,
    )
