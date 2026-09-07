from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, HttpResponse

from gradmatch.accounts.models import User

from .models import GuestSession

GUEST_CAPABILITY_COOKIE = "gradmatch_guest_capability"
DEFAULT_GUEST_CAPABILITY_LIFETIME = timedelta(hours=24)


def create_guest_session(
    *,
    now: datetime,
    lifetime: timedelta = DEFAULT_GUEST_CAPABILITY_LIFETIME,
) -> tuple[GuestSession, str]:
    token = secrets.token_urlsafe(32)
    guest_session = GuestSession.objects.create(
        token_digest=_token_digest(token),
        expires_at=now + lifetime,
    )
    return guest_session, token


def resolve_guest_session(*, token: str, now: datetime) -> GuestSession | None:
    candidate_digest = _token_digest(token)
    guest_session = GuestSession.objects.filter(token_digest=candidate_digest).first()
    if guest_session is None:
        return None
    if not hmac.compare_digest(guest_session.token_digest, candidate_digest):
        return None
    if guest_session.revoked_at is not None or guest_session.expires_at <= now:
        return None
    return guest_session


def request_can_access_guest_session(
    *,
    request: HttpRequest,
    guest_session: GuestSession,
    user: User | None,
    now: datetime,
) -> bool:
    if guest_session.owner is not None and user is not None:
        return guest_session.owner.pk == user.pk
    token = request.COOKIES.get(GUEST_CAPABILITY_COOKIE)
    if token is None:
        return False
    resolved = resolve_guest_session(token=token, now=now)
    return resolved is not None and resolved.pk == guest_session.pk


@transaction.atomic
def claim_guest_session(
    *,
    guest_session_id: UUID,
    token: str,
    user: User,
    now: datetime,
) -> GuestSession:
    guest_session = GuestSession.objects.select_for_update().get(pk=guest_session_id)
    resolved = resolve_guest_session(token=token, now=now)
    if resolved is None or resolved.pk != guest_session.pk or guest_session.owner is not None:
        raise PermissionError("The guest capability is invalid or has already been claimed.")
    guest_session.owner = user
    guest_session.claimed_at = now
    guest_session.revoked_at = now
    guest_session.token_digest = _token_digest(secrets.token_urlsafe(32))
    guest_session.save(
        update_fields=("owner", "claimed_at", "revoked_at", "token_digest")
    )
    # Notifications created while the decision belonged to an anonymous
    # capability become account notifications when that capability is claimed.
    from gradmatch.support.models import SnapshotUpdateNotification

    SnapshotUpdateNotification.objects.filter(
        snapshot_update__old_snapshot__comparison_result__run__guest_session=(
            guest_session
        ),
        recipient__isnull=True,
    ).update(recipient=user)
    return guest_session


def set_guest_capability_cookie(
    response: HttpResponse,
    *,
    token: str,
    lifetime: timedelta = DEFAULT_GUEST_CAPABILITY_LIFETIME,
) -> None:
    response.set_cookie(
        GUEST_CAPABILITY_COOKIE,
        token,
        max_age=int(lifetime.total_seconds()),
        path="/api/v1",
        secure=settings.SECURE_COOKIES,
        httponly=True,
        samesite="Lax",
    )


def clear_guest_capability_cookie(response: HttpResponse) -> None:
    response.delete_cookie(
        GUEST_CAPABILITY_COOKIE,
        path="/api/v1",
        samesite="Lax",
    )


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
