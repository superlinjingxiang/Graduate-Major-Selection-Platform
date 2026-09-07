from __future__ import annotations

import pytest
from allauth.account.models import EmailAddress
from django.test import Client
from django.utils import timezone

from gradmatch.accounts.models import User
from gradmatch.advising.capabilities import GUEST_CAPABILITY_COOKIE
from gradmatch.advising.models import DecisionSnapshot, GuestSession
from gradmatch.support.models import OutboxEvent, SnapshotUpdate, SnapshotUpdateNotification


def create_guest_snapshot(client: Client) -> tuple[str, str]:
    fact_response = client.post(
        "/api/v1/fact-sets",
        data={
            "confirmed_facts": {
                "target_year": 2027,
                "region": "北京",
                "study_mode": "full_time",
                "admission_pathway": "unified_exam",
            }
        },
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
    snapshot_response = client.post(
        "/api/v1/decision-snapshots",
        data={"comparison_run_id": comparison_id},
        content_type="application/json",
    )
    return comparison_id, snapshot_response.json()["snapshot_id"]


@pytest.mark.django_db
def test_current_pilot_snapshot_uses_awaiting_official_information(client: Client) -> None:
    comparison_id, snapshot_id = create_guest_snapshot(client)

    response = client.get(f"/api/v1/decision-snapshots/{snapshot_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparison_run_id"] == comparison_id
    assert payload["outcome"] == DecisionSnapshot.Outcome.AWAITING_OFFICIAL_INFORMATION.value
    assert payload["retained"] == []
    assert payload["excluded"] == []
    assert len(payload["deferred"]) == 3
    assert payload["key_unknowns"] == ["rule_unpublished"]
    assert payload["next_actions"] == ["等待并复核 2027 官方招生信息"]
    serialized = response.content.decode()
    assert "token" not in serialized
    assert "digest" not in serialized
    assert "test_fixture" not in serialized


@pytest.mark.django_db
def test_snapshot_claim_requires_login_and_the_valid_capability(client: Client) -> None:
    _, snapshot_id = create_guest_snapshot(client)
    original_token = client.cookies[GUEST_CAPABILITY_COOKIE].value
    snapshot = DecisionSnapshot.objects.get(pk=snapshot_id)
    event = OutboxEvent.objects.create(
        event_key="correction.claim-published:claim-notification",
        event_type="correction.claim_published",
        payload={},
        published_at=timezone.now(),
    )
    update = SnapshotUpdate.objects.create(
        outbox_event=event,
        old_snapshot=snapshot,
        old_result=snapshot.comparison_result,
        new_result=snapshot.comparison_result,
        diff={"group_changes": {}},
    )
    notification = SnapshotUpdateNotification.objects.create(snapshot_update=update)

    unauthenticated = client.post(f"/api/v1/decision-snapshots/{snapshot_id}/claim")
    assert unauthenticated.status_code == 401

    user = User.objects.create_user(
        email="snapshot-owner@example.test",
        password="strong-password-123",
    )
    client.force_login(user)
    unverified = client.post(f"/api/v1/decision-snapshots/{snapshot_id}/claim")
    assert unverified.status_code == 403
    assert GuestSession.objects.get().owner is None

    EmailAddress.objects.create(
        user=user,
        email=user.email,
        verified=True,
        primary=True,
    )
    claimed = client.post(f"/api/v1/decision-snapshots/{snapshot_id}/claim")

    assert claimed.status_code == 200
    guest_session = GuestSession.objects.get()
    assert guest_session.owner == user
    assert guest_session.claimed_at is not None
    assert guest_session.revoked_at is not None
    notification.refresh_from_db()
    assert notification.recipient == user
    assert claimed.cookies[GUEST_CAPABILITY_COOKIE]["max-age"] == 0
    assert client.get(f"/api/v1/decision-snapshots/{snapshot_id}").status_code == 200

    replay_user = User.objects.create_user(
        email="snapshot-replay@example.test",
        password="strong-password-123",
    )
    replay = Client()
    replay.force_login(replay_user)
    replay.cookies[GUEST_CAPABILITY_COOKIE] = original_token
    assert replay.post(f"/api/v1/decision-snapshots/{snapshot_id}/claim").status_code == 404


@pytest.mark.django_db
def test_logged_in_user_without_capability_cannot_claim_guest_snapshot(client: Client) -> None:
    _, snapshot_id = create_guest_snapshot(client)
    user = User.objects.create_user(
        email="no-capability@example.test",
        password="strong-password-123",
    )
    stranger = Client()
    stranger.force_login(user)

    response = stranger.post(f"/api/v1/decision-snapshots/{snapshot_id}/claim")

    assert response.status_code == 404
