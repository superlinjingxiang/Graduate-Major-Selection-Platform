from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client, override_settings
from django.utils import timezone

from gradmatch.advising.capabilities import (
    GUEST_CAPABILITY_COOKIE,
    create_guest_session,
    resolve_guest_session,
)
from gradmatch.advising.models import GuestSession


@pytest.mark.django_db
def test_guest_session_stores_only_a_digest_and_expires() -> None:
    now = timezone.now()

    guest_session, token = create_guest_session(now=now, lifetime=timedelta(minutes=5))

    assert token not in guest_session.token_digest
    assert len(guest_session.token_digest) == 64
    assert resolve_guest_session(token=token, now=now) == guest_session
    assert resolve_guest_session(token="wrong-token", now=now) is None
    assert resolve_guest_session(token=token, now=now + timedelta(minutes=6)) is None


@override_settings(SECURE_COOKIES=True)
@pytest.mark.django_db
def test_fact_set_creation_places_capability_only_in_a_secure_cookie(client: Client) -> None:
    response = client.post(
        "/api/v1/fact-sets",
        data={"confirmed_facts": {"target_year": 2027}},
        content_type="application/json",
    )

    assert response.status_code == 201
    cookie = response.cookies[GUEST_CAPABILITY_COOKIE]
    token = cookie.value
    assert cookie["secure"] is True
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/api/v1"
    guest_session = GuestSession.objects.get()
    assert token not in guest_session.token_digest
    assert token not in response.content.decode()


@pytest.mark.django_db
def test_comparison_uuid_is_not_an_access_credential(client: Client) -> None:
    fact_response = client.post(
        "/api/v1/fact-sets",
        data={"confirmed_facts": {"target_year": 2027}},
        content_type="application/json",
    )
    comparison_response = client.post(
        "/api/v1/comparison-runs",
        data={
            "fact_set_id": fact_response.json()["fact_set_id"],
            "fact_revision": 1,
        },
        content_type="application/json",
    )
    comparison_id = comparison_response.json()["comparison_run_id"]

    assert client.get(f"/api/v1/comparison-runs/{comparison_id}").status_code == 200

    stranger = Client()
    assert stranger.get(f"/api/v1/comparison-runs/{comparison_id}").status_code == 404
    stranger.cookies[GUEST_CAPABILITY_COOKIE] = "invalid-capability"
    assert stranger.get(f"/api/v1/comparison-runs/{comparison_id}").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "offering_ids",
    [[], ["ao_2027_bupt_085404_ft_unified_plan01"]],
)
def test_comparison_api_rejects_an_invalid_engineering_selection(
    client: Client,
    offering_ids: list[str],
) -> None:
    fact_response = client.post(
        "/api/v1/fact-sets",
        data={"confirmed_facts": {"target_year": 2027}},
        content_type="application/json",
    )

    response = client.post(
        "/api/v1/comparison-runs",
        data={
            "fact_set_id": fact_response.json()["fact_set_id"],
            "fact_revision": 1,
            "offering_ids": offering_ids,
        },
        content_type="application/json",
    )

    assert response.status_code == 422
