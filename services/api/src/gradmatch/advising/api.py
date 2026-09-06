from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, cast
from uuid import UUID

from allauth.account.models import EmailAddress
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema, Status
from ninja.errors import HttpError
from ninja.security import django_auth
from pydantic import ConfigDict, Field, StrictBool, StrictInt, StringConstraints

from gradmatch.accounts.authentication import x_session_token_header_auth
from gradmatch.accounts.models import User
from gradmatch.catalog.models import AnnualOffering
from gradmatch.catalog.seed import ENGINEERING_SLICE_OFFERING_IDS, PILOT_MANIFEST_KEY

from .capabilities import (
    GUEST_CAPABILITY_COOKIE,
    claim_guest_session,
    clear_guest_capability_cookie,
    create_guest_session,
    request_can_access_guest_session,
    set_guest_capability_cookie,
)
from .comparison import (
    create_comparison_run,
    create_decision_snapshot,
    latest_comparison_result,
)
from .eligibility import assess_eligibility, canonical_facts_hash
from .models import (
    ComparisonRun,
    ComparisonRunResult,
    DecisionSnapshot,
    EligibilityAssessment,
    FactSet,
    FactSetRevision,
    GuestSession,
)

router = Router(tags=["advising"])

NormalizedText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]
NonNegativeYears = Annotated[StrictInt, Field(ge=0, le=80)]


class ConfirmedFacts(Schema):
    model_config = ConfigDict(extra="forbid")

    age_18_or_over: StrictBool | None = None
    target_year: Literal[2027] | None = None
    region: Literal["北京"] | None = None
    study_mode: Literal["full_time"] | None = None
    admission_pathway: Literal["unified_exam"] | None = None
    education_level: Literal["bachelor", "equivalent", "other"] | None = None
    undergraduate_major: NormalizedText | None = None
    equivalent_education: StrictBool | None = None
    cross_discipline: StrictBool | None = None
    years_of_work_experience: NonNegativeYears | None = None
    overseas_degree_certified: StrictBool | None = None
    directed_employment_confirmed: StrictBool | None = None


class FactSetCreateRequest(Schema):
    model_config = ConfigDict(extra="forbid")

    confirmed_facts: ConfirmedFacts


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


class ComparisonRunCreateRequest(Schema):
    model_config = ConfigDict(extra="forbid")

    fact_set_id: UUID
    fact_revision: int
    offering_ids: list[str] | None = None


class ComparisonRunResponse(Schema):
    comparison_run_id: UUID
    result_version: int
    result_hash: str
    manifest_key: str
    order: list[str]
    groups: dict[str, list[str]]
    assessments: list[dict[str, object]]


class DecisionSnapshotCreateRequest(Schema):
    model_config = ConfigDict(extra="forbid")

    comparison_run_id: UUID
    requested_outcome: str | None = None


class DecisionSnapshotResponse(Schema):
    snapshot_id: UUID
    comparison_run_id: UUID
    comparison_result_version: int
    comparison_result_hash: str
    outcome: str
    retained: list[str]
    excluded: list[str]
    deferred: list[str]
    user_confirmed_reasons: list[str]
    key_unknowns: list[str]
    next_actions: list[str]
    revisit_date: date | None
    snapshot_hash: str
    created_at: datetime


@router.post("/fact-sets", response={201: FactSetResponse}, operation_id="create_fact_set")
def create_fact_set(
    request: HttpRequest,
    response: HttpResponse,
    payload: FactSetCreateRequest,
) -> Status[FactSetResponse]:
    confirmed_facts = cast(
        dict[str, object],
        payload.confirmed_facts.model_dump(exclude_none=True),
    )

    request_user = cast(object, getattr(request, "user", None))
    owner = request_user if isinstance(request_user, User) else None
    guest_session: GuestSession | None = None
    guest_token: str | None = None
    with transaction.atomic():
        if owner is None:
            guest_session, guest_token = create_guest_session(now=timezone.now())
        fact_set = FactSet.objects.create(owner=owner, guest_session=guest_session)
        revision = FactSetRevision.objects.create(
            fact_set=fact_set,
            version=1,
            confirmed_facts=confirmed_facts,
            input_hash=canonical_facts_hash(confirmed_facts),
        )
    if guest_token is not None:
        set_guest_capability_cookie(response, token=guest_token)
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
    offering = get_object_or_404(
        AnnualOffering.objects.filter(manifest_entries__manifest__key=PILOT_MANIFEST_KEY),
        pk=payload.offering_id,
    )
    fact_revision = get_object_or_404(
        FactSetRevision.objects.select_related(
            "fact_set__owner",
            "fact_set__guest_session__owner",
        ),
        fact_set_id=payload.fact_set_id,
        version=payload.fact_revision,
    )
    _require_fact_set_access(request, fact_revision.fact_set)
    assessment = assess_eligibility(
        offering=offering,
        fact_revision=fact_revision,
    )
    return Status(201, _serialize_assessment(assessment))


@router.post(
    "/comparison-runs",
    response={201: ComparisonRunResponse},
    operation_id="create_comparison_run",
)
def create_comparison(
    request: HttpRequest,
    payload: ComparisonRunCreateRequest,
) -> Status[ComparisonRunResponse]:
    fact_revision = get_object_or_404(
        FactSetRevision.objects.select_related(
            "fact_set__owner",
            "fact_set__guest_session__owner",
        ),
        fact_set_id=payload.fact_set_id,
        version=payload.fact_revision,
    )
    _require_fact_set_access(request, fact_revision.fact_set)
    offering_ids = (
        ENGINEERING_SLICE_OFFERING_IDS
        if payload.offering_ids is None
        else payload.offering_ids
    )
    try:
        result = create_comparison_run(
            fact_revision=fact_revision,
            offering_ids=offering_ids,
            owner=fact_revision.fact_set.owner,
            guest_session=fact_revision.fact_set.guest_session,
        )
    except ValueError as error:
        raise HttpError(422, str(error)) from error
    return Status(201, _serialize_comparison(result))


@router.get(
    "/comparison-runs/{comparison_run_id}",
    response=ComparisonRunResponse,
    operation_id="get_comparison_run",
)
def get_comparison(
    request: HttpRequest,
    comparison_run_id: UUID,
) -> ComparisonRunResponse:
    run = _get_accessible_comparison_run(request, comparison_run_id)
    return _serialize_comparison(latest_comparison_result(run))


@router.post(
    "/decision-snapshots",
    response={201: DecisionSnapshotResponse},
    operation_id="create_decision_snapshot",
)
def create_snapshot(
    request: HttpRequest,
    payload: DecisionSnapshotCreateRequest,
) -> Status[DecisionSnapshotResponse]:
    run = _get_accessible_comparison_run(request, payload.comparison_run_id)
    try:
        snapshot = create_decision_snapshot(
            comparison_result=latest_comparison_result(run),
            requested_outcome=payload.requested_outcome,
        )
    except ValueError as error:
        raise HttpError(422, str(error)) from error
    return Status(201, _serialize_snapshot(snapshot))


@router.get(
    "/decision-snapshots/{snapshot_id}",
    response=DecisionSnapshotResponse,
    operation_id="get_decision_snapshot",
)
def get_snapshot(request: HttpRequest, snapshot_id: UUID) -> DecisionSnapshotResponse:
    snapshot = get_object_or_404(
        DecisionSnapshot.objects.select_related(
            "comparison_result__run__owner",
            "comparison_result__run__guest_session__owner",
        ),
        pk=snapshot_id,
    )
    _require_comparison_access(request, snapshot.comparison_result.run)
    return _serialize_snapshot(snapshot)


@router.post(
    "/decision-snapshots/{snapshot_id}/claim",
    auth=[django_auth, x_session_token_header_auth],
    response=DecisionSnapshotResponse,
    operation_id="claim_decision_snapshot",
)
def claim_snapshot(
    request: HttpRequest,
    response: HttpResponse,
    snapshot_id: UUID,
) -> DecisionSnapshotResponse:
    snapshot = get_object_or_404(
        DecisionSnapshot.objects.select_related(
            "comparison_result__run__guest_session",
        ),
        pk=snapshot_id,
    )
    run = snapshot.comparison_result.run
    guest_session = run.guest_session
    token = request.COOKIES.get(GUEST_CAPABILITY_COOKIE)
    user = _request_user(request)
    if guest_session is None or token is None or user is None:
        raise HttpError(404, "Decision snapshot not found.")
    if not request_can_access_guest_session(
        request=request,
        guest_session=guest_session,
        user=user,
        now=timezone.now(),
    ):
        raise HttpError(404, "Decision snapshot not found.")
    if not EmailAddress.objects.filter(user=user, verified=True, primary=True).exists():
        raise HttpError(403, "A verified primary email is required.")
    try:
        claim_guest_session(
            guest_session_id=guest_session.pk,
            token=token,
            user=user,
            now=timezone.now(),
        )
    except PermissionError as error:
        raise HttpError(404, "Decision snapshot not found.") from error
    clear_guest_capability_cookie(response)
    return _serialize_snapshot(snapshot)


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


def _serialize_comparison(result: ComparisonRunResult) -> ComparisonRunResponse:
    payload = result.result
    return ComparisonRunResponse(
        comparison_run_id=result.run.pk,
        result_version=result.version,
        result_hash=result.result_hash,
        manifest_key=cast(str, payload["manifest_key"]),
        order=cast(list[str], payload["order"]),
        groups=cast(dict[str, list[str]], payload["groups"]),
        assessments=cast(list[dict[str, object]], payload["assessments"]),
    )


def _serialize_snapshot(snapshot: DecisionSnapshot) -> DecisionSnapshotResponse:
    comparison_result = snapshot.comparison_result
    return DecisionSnapshotResponse(
        snapshot_id=snapshot.pk,
        comparison_run_id=comparison_result.run.pk,
        comparison_result_version=comparison_result.version,
        comparison_result_hash=comparison_result.result_hash,
        outcome=snapshot.outcome,
        retained=snapshot.retained,
        excluded=snapshot.excluded,
        deferred=snapshot.deferred,
        user_confirmed_reasons=snapshot.user_confirmed_reasons,
        key_unknowns=snapshot.key_unknowns,
        next_actions=snapshot.next_actions,
        revisit_date=snapshot.revisit_date,
        snapshot_hash=snapshot.snapshot_hash,
        created_at=snapshot.created_at,
    )


def _get_accessible_comparison_run(
    request: HttpRequest,
    comparison_run_id: UUID,
) -> ComparisonRun:
    run = get_object_or_404(
        ComparisonRun.objects.select_related("owner", "guest_session__owner"),
        pk=comparison_run_id,
    )
    _require_comparison_access(request, run)
    return run


def _require_fact_set_access(request: HttpRequest, fact_set: FactSet) -> None:
    user = _request_user(request)
    if fact_set.owner is not None and user is not None and fact_set.owner.pk == user.pk:
        return
    if fact_set.guest_session is not None and request_can_access_guest_session(
        request=request,
        guest_session=fact_set.guest_session,
        user=user,
        now=timezone.now(),
    ):
        return
    raise HttpError(404, "Fact set not found.")


def _require_comparison_access(request: HttpRequest, run: ComparisonRun) -> None:
    user = _request_user(request)
    if run.owner is not None and user is not None and run.owner.pk == user.pk:
        return
    if run.guest_session is not None and request_can_access_guest_session(
        request=request,
        guest_session=run.guest_session,
        user=user,
        now=timezone.now(),
    ):
        return
    raise HttpError(404, "Comparison run not found.")


def _request_user(request: HttpRequest) -> User | None:
    request_auth = cast(object, getattr(request, "auth", None))
    if isinstance(request_auth, User):
        return request_auth
    request_user = cast(object, getattr(request, "user", None))
    return request_user if isinstance(request_user, User) else None
