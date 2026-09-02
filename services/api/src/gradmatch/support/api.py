from __future__ import annotations

from typing import cast
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Field, Router, Schema, Status
from pydantic import ConfigDict, HttpUrl

from gradmatch.accounts.models import User
from gradmatch.advising.capabilities import (
    GUEST_CAPABILITY_COOKIE,
    create_guest_session,
    request_can_access_guest_session,
    resolve_guest_session,
    set_guest_capability_cookie,
)
from gradmatch.advising.models import GuestSession
from gradmatch.catalog.models import AnnualOffering
from gradmatch.catalog.seed import PILOT_MANIFEST_KEY

from .models import CorrectionCase
from .services import submit_correction

router = Router(tags=["support"])


class CorrectionCreateRequest(Schema):
    model_config = ConfigDict(extra="forbid")

    offering_id: str
    field_key: str = Field(min_length=1, max_length=160)
    proposed_source_url: HttpUrl
    explanation: str = Field(min_length=10, max_length=4000)


class CorrectionResponse(Schema):
    correction_id: UUID
    offering_id: str
    field_key: str
    proposed_source_url: str
    explanation: str
    status: str


@router.post(
    "/corrections",
    response={201: CorrectionResponse},
    operation_id="create_correction",
)
def create_correction(
    request: HttpRequest,
    response: HttpResponse,
    payload: CorrectionCreateRequest,
) -> Status[CorrectionResponse]:
    offering = get_object_or_404(
        AnnualOffering.objects.filter(manifest_entries__manifest__key=PILOT_MANIFEST_KEY),
        pk=payload.offering_id,
    )
    user = _request_user(request)
    guest_session: GuestSession | None = None
    guest_token: str | None = None
    if user is None:
        existing_token = request.COOKIES.get(GUEST_CAPABILITY_COOKIE)
        if existing_token is not None:
            guest_session = resolve_guest_session(token=existing_token, now=timezone.now())
        if guest_session is None:
            guest_session, guest_token = create_guest_session(now=timezone.now())

    case = submit_correction(
        offering=offering,
        field_key=payload.field_key,
        proposed_source_url=str(payload.proposed_source_url),
        explanation=payload.explanation,
        submitter=user,
        guest_session=guest_session,
    )
    if guest_token is not None:
        set_guest_capability_cookie(response, token=guest_token)
    return Status(201, _serialize(case))


@router.get(
    "/corrections/{correction_id}",
    response=CorrectionResponse,
    operation_id="get_correction",
)
def get_correction(request: HttpRequest, correction_id: UUID) -> CorrectionResponse:
    case = get_object_or_404(
        CorrectionCase.objects.select_related("submitter", "guest_session__owner"),
        pk=correction_id,
    )
    user = _request_user(request)
    if case.submitter is not None:
        if user is None or user.pk != case.submitter.pk:
            return _not_found()
    elif case.guest_session is None or not request_can_access_guest_session(
        request=request,
        guest_session=case.guest_session,
        user=user,
        now=timezone.now(),
    ):
        return _not_found()
    return _serialize(case)


def _serialize(case: CorrectionCase) -> CorrectionResponse:
    return CorrectionResponse(
        correction_id=case.pk,
        offering_id=case.offering.pk,
        field_key=case.field_key,
        proposed_source_url=case.proposed_source_url,
        explanation=case.explanation,
        status=case.status,
    )


def _request_user(request: HttpRequest) -> User | None:
    request_auth = cast(object, getattr(request, "auth", None))
    if isinstance(request_auth, User):
        return request_auth
    request_user = cast(object, getattr(request, "user", None))
    return request_user if isinstance(request_user, User) else None


def _not_found() -> CorrectionResponse:
    from ninja.errors import HttpError

    raise HttpError(404, "Correction not found.")
