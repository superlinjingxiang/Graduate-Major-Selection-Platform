from __future__ import annotations

import json

import pytest
from advising.factories import (
    approve_claim,
    create_claim,
    create_reviewer,
    create_source_document,
)
from django.test import Client
from django.utils import timezone

from gradmatch.accounts.models import User
from gradmatch.advising.models import EvidenceClaimRevision, PublicationEvent, ReviewDecision
from gradmatch.advising.publication import publish_claim
from gradmatch.support.models import AuditEvent, CorrectionCase, OutboxEvent
from gradmatch.support.services import (
    CorrectionWorkflowError,
    accept_correction,
    publish_correction,
    reject_correction,
)

OFFERING_ID = "ao_2027_bupt_081200_ft_unified_plan01"


def submit_correction(client: Client) -> tuple[str, dict[str, object]]:
    response = client.post(
        "/api/v1/corrections",
        data=json.dumps(
            {
                "offering_id": OFFERING_ID,
                "field_key": "eligibility.sample_rule",
                "proposed_source_url": "https://yzb.example.edu/2027/rules",
                "explanation": "官方页面显示的资格条件与当前记录不同。",
            }
        ),
        content_type="application/json",
    )
    return str(response.json()["correction_id"]), response.json()


@pytest.mark.django_db
def test_anonymous_submitter_can_only_read_submitter_safe_status(client: Client) -> None:
    correction_id, payload = submit_correction(client)

    assert payload == {
        "correction_id": correction_id,
        "offering_id": OFFERING_ID,
        "field_key": "eligibility.sample_rule",
        "proposed_source_url": "https://yzb.example.edu/2027/rules",
        "explanation": "官方页面显示的资格条件与当前记录不同。",
        "status": "submitted",
    }
    cookie = client.cookies["gradmatch_guest_capability"]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"

    case = CorrectionCase.objects.get(pk=correction_id)
    case.reviewer_note = "internal reviewer-only note"
    case.save(update_fields=("reviewer_note", "updated_at"))

    detail = client.get(f"/api/v1/corrections/{correction_id}")
    serialized = json.dumps(detail.json())
    assert detail.status_code == 200
    assert "reviewer_note" not in serialized
    assert "accepted_claim" not in serialized
    assert "token" not in serialized
    assert "digest" not in serialized

    stranger = Client()
    assert stranger.get(f"/api/v1/corrections/{correction_id}").status_code == 404


@pytest.mark.django_db
def test_signed_in_submitter_owns_the_correction() -> None:
    user = User.objects.create_user(
        email="correction-owner@example.test",
        password="strong-password-123",
    )
    client = Client()
    client.force_login(user)

    correction_id, _ = submit_correction(client)

    case = CorrectionCase.objects.get(pk=correction_id)
    assert case.submitter == user
    assert case.guest_session is None
    assert client.get(f"/api/v1/corrections/{correction_id}").status_code == 200


@pytest.mark.django_db
def test_only_staff_can_accept_publish_or_reject_a_correction(client: Client) -> None:
    correction_id, _ = submit_correction(client)
    non_staff = User.objects.create_user(
        email="not-staff@example.test",
        password="strong-password-123",
    )
    replacement_source = create_source_document()

    with pytest.raises(CorrectionWorkflowError, match="staff"):
        accept_correction(
            correction_id=correction_id,
            reviewer=non_staff,
            source_document=replacement_source,
            normalized_value=False,
            original_value="false",
            reviewer_note="not authorized",
            now=timezone.now(),
        )
    with pytest.raises(CorrectionWorkflowError, match="staff"):
        publish_correction(
            correction_id=correction_id,
            reviewer=non_staff,
            now=timezone.now(),
        )
    with pytest.raises(CorrectionWorkflowError, match="staff"):
        reject_correction(
            correction_id=correction_id,
            reviewer=non_staff,
            reviewer_note="not authorized",
            now=timezone.now(),
        )


@pytest.mark.django_db
def test_accept_and_publish_create_revision_audit_and_outbox_atomically(client: Client) -> None:
    reviewer = create_reviewer()
    original = create_claim(create_source_document(), normalized_value=True)
    approve_claim(original, reviewer)
    publish_claim(claim_id=original.pk, reviewer=reviewer, now=timezone.now())
    correction_id, _ = submit_correction(client)

    accepted = accept_correction(
        correction_id=correction_id,
        reviewer=reviewer,
        source_document=create_source_document(),
        normalized_value=False,
        original_value="false",
        reviewer_note="Source confirms the correction.",
        now=timezone.now(),
    )
    event = publish_correction(
        correction_id=correction_id,
        reviewer=reviewer,
        now=timezone.now(),
    )

    accepted.refresh_from_db()
    assert accepted.accepted_claim is not None
    replacement = EvidenceClaimRevision.objects.get(pk=accepted.accepted_claim.pk)
    assert replacement.supersedes == original
    assert replacement.revision == 2
    assert replacement.normalized_value is False
    assert ReviewDecision.objects.filter(
        claim=replacement,
        reviewer=reviewer,
        outcome=ReviewDecision.Outcome.APPROVED,
    ).exists()
    assert PublicationEvent.objects.filter(claim=replacement).count() == 1
    assert event.payload == {
        "correction_id": correction_id,
        "publication_event_id": PublicationEvent.objects.get(claim=replacement).pk,
        "superseded_claim_id": original.pk,
        "replacement_claim_id": replacement.pk,
        "revised_rule_set_ids": [],
    }
    assert event.processing_state == OutboxEvent.ProcessingState.PENDING
    assert AuditEvent.objects.filter(target_id=correction_id).count() == 2
    assert CorrectionCase.objects.get(pk=correction_id).status == CorrectionCase.Status.PUBLISHED


@pytest.mark.django_db
def test_correction_cannot_publish_before_acceptance(client: Client) -> None:
    reviewer = create_reviewer()
    correction_id, _ = submit_correction(client)

    with pytest.raises(CorrectionWorkflowError, match="accepted"):
        publish_correction(
            correction_id=correction_id,
            reviewer=reviewer,
            now=timezone.now(),
        )
    assert OutboxEvent.objects.count() == 0
    assert PublicationEvent.objects.count() == 0


@pytest.mark.django_db
def test_fixture_evidence_cannot_be_accepted_as_a_production_correction(
    client: Client,
) -> None:
    reviewer = create_reviewer()
    original = create_claim(create_source_document(), normalized_value=True)
    approve_claim(original, reviewer)
    publish_claim(claim_id=original.pk, reviewer=reviewer, now=timezone.now())
    correction_id, _ = submit_correction(client)

    with pytest.raises(CorrectionWorkflowError, match="current-year production evidence"):
        accept_correction(
            correction_id=correction_id,
            reviewer=reviewer,
            source_document=create_source_document(
                data_class="synthetic",
                reference_year=2026,
            ),
            normalized_value=False,
            original_value="false",
            reviewer_note="fixture must remain isolated",
            now=timezone.now(),
        )

    assert CorrectionCase.objects.get(pk=correction_id).status == "submitted"
    assert EvidenceClaimRevision.objects.filter(claim_key=original.claim_key).count() == 1
