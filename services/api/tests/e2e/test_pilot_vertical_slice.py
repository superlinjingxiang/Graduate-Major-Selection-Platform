from __future__ import annotations

import json
import socket
from typing import cast

import pytest
from advising.factories import (
    approve_claim,
    create_claim,
    create_reviewer,
    create_rule_set,
    create_rule_with_evidence,
    create_source_document,
)
from allauth.account.models import EmailAddress
from django.test import Client
from django.utils import timezone

from gradmatch.accounts.models import User
from gradmatch.advising.capabilities import GUEST_CAPABILITY_COOKIE
from gradmatch.advising.models import (
    ComparisonRunResult,
    DecisionSnapshot,
    EvidenceClaimRevision,
    RuleSetRevision,
    SourceDocumentRevision,
)
from gradmatch.advising.publication import publish_claim, publish_rule_set
from gradmatch.catalog.seed import PILOT_MANIFEST_KEY
from gradmatch.support.models import JobExecution, OutboxEvent, SnapshotUpdate
from gradmatch.support.services import accept_correction, publish_correction
from gradmatch.support.tasks import recompute_published_correction


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network_connection(*args: object, **kwargs: object) -> socket.socket:
        del args, kwargs
        raise AssertionError("The pilot vertical slice must not open a network connection.")

    monkeypatch.setattr(socket, "create_connection", fail_network_connection)


def _post_json(client: Client, path: str, payload: dict[str, object]):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def _publish_offering_rule_set(
    *,
    reviewer: User,
    offering_id: str,
    coverage_complete: bool,
) -> tuple[EvidenceClaimRevision, RuleSetRevision]:
    from gradmatch.catalog.models import AnnualOffering

    offering = AnnualOffering.objects.get(pk=offering_id)
    claim = create_claim(
        create_source_document(),
        offering=offering,
        normalized_value=True,
    )
    approve_claim(claim, reviewer)
    publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())
    rule_set = create_rule_set(coverage_complete=coverage_complete)
    create_rule_with_evidence(rule_set, claim)
    publish_rule_set(rule_set_id=rule_set.pk, reviewer=reviewer, now=timezone.now())
    return claim, rule_set


@pytest.mark.django_db
def test_first_pilot_vertical_slice_is_safe_reproducible_and_idempotent(
    client: Client,
) -> None:
    reviewer = create_reviewer()
    engineering_ids = [
        "ao_2027_bupt_081200_ft_unified_plan01",
        "ao_2027_bit_085404_ft_unified_plan01",
        "ao_2027_bjut_085410_ft_unified_plan01",
    ]

    # Keep an explicit 2026 fixture in the same database to prove production reads isolate it.
    fixture_claim = create_claim(
        create_source_document(
            data_class=SourceDocumentRevision.DataClass.SYNTHETIC,
            reference_year=2026,
        )
    )
    approve_claim(fixture_claim, reviewer)
    publish_claim(claim_id=fixture_claim.pk, reviewer=reviewer, now=timezone.now())
    fixture_rules = create_rule_set(
        namespace=RuleSetRevision.Namespace.TEST_FIXTURE,
        reference_year=2026,
    )
    create_rule_with_evidence(fixture_rules, fixture_claim)
    publish_rule_set(rule_set_id=fixture_rules.pk, reviewer=reviewer, now=timezone.now())

    bupt_claim, bupt_rules = _publish_offering_rule_set(
        reviewer=reviewer,
        offering_id=engineering_ids[0],
        coverage_complete=False,
    )
    _, bit_rules = _publish_offering_rule_set(
        reviewer=reviewer,
        offering_id=engineering_ids[1],
        coverage_complete=True,
    )

    scope_response = client.get("/api/v1/pilot-scope")
    offerings_response = client.get("/api/v1/offerings")
    assert scope_response.status_code == 200
    assert offerings_response.status_code == 200
    assert scope_response.json()["key"] == PILOT_MANIFEST_KEY
    assert scope_response.json()["offering_count"] == 10
    catalog_ids = {item["id"] for item in offerings_response.json()["items"]}
    assert set(engineering_ids).issubset(catalog_ids)

    fact_response = _post_json(
        client,
        "/api/v1/fact-sets",
        {
            "confirmed_facts": {
                "target_year": 2027,
                "region": "北京",
                "study_mode": "full_time",
                "admission_pathway": "unified_exam",
            }
        },
    )
    assert fact_response.status_code == 201
    fact_payload = fact_response.json()
    capability = client.cookies[GUEST_CAPABILITY_COOKIE].value

    assessments: list[dict[str, object]] = []
    for offering_id in engineering_ids:
        response = _post_json(
            client,
            "/api/v1/eligibility-assessments",
            {
                "offering_id": offering_id,
                "fact_set_id": fact_payload["fact_set_id"],
                "fact_revision": fact_payload["version"],
            },
        )
        assert response.status_code == 201
        assessments.append(response.json())

    assert [item["status"] for item in assessments] == ["needs_confirmation"] * 3
    assert assessments[0]["rule_set_key"] == bupt_rules.key
    assert assessments[0]["reasons"] == [
        {"code": "rule_set_incomplete", "fact_key": None, "rule_key": None}
    ]
    assert assessments[1]["rule_set_key"] == bit_rules.key
    assert assessments[1]["reasons"] == [
        {
            "code": "user_fact_missing",
            "fact_key": "sample_fact",
            "rule_key": "sample-rule",
        }
    ]
    assert assessments[2]["rule_set_key"] is None
    assert assessments[2]["reasons"] == [
        {"code": "rule_unpublished", "fact_key": None, "rule_key": None}
    ]

    comparison_response = _post_json(
        client,
        "/api/v1/comparison-runs",
        {
            "fact_set_id": fact_payload["fact_set_id"],
            "fact_revision": fact_payload["version"],
            "offering_ids": engineering_ids,
        },
    )
    assert comparison_response.status_code == 201
    comparison_payload = comparison_response.json()
    assert comparison_payload["groups"] == {
        "eligible_known": [],
        "ineligible_known": [],
        "needs_confirmation": engineering_ids,
    }

    snapshot_response = _post_json(
        client,
        "/api/v1/decision-snapshots",
        {"comparison_run_id": comparison_payload["comparison_run_id"]},
    )
    assert snapshot_response.status_code == 201
    snapshot_payload = snapshot_response.json()
    assert snapshot_payload["outcome"] == "awaiting_official_information"
    assert snapshot_payload["retained"] == []
    assert snapshot_payload["excluded"] == []
    assert snapshot_payload["deferred"] == engineering_ids

    original_result = ComparisonRunResult.objects.get(
        run_id=comparison_payload["comparison_run_id"],
        version=1,
    )
    original_result_payload = dict(original_result.result)
    original_snapshot = DecisionSnapshot.objects.get(pk=snapshot_payload["snapshot_id"])
    original_snapshot_hash = original_snapshot.snapshot_hash

    owner = User.objects.create_user(
        email="pilot-owner@example.test",
        password="strong-password-123",
    )
    EmailAddress.objects.create(
        user=owner,
        email=owner.email,
        verified=True,
        primary=True,
    )
    client.force_login(owner)
    client.cookies[GUEST_CAPABILITY_COOKIE] = capability
    claim_response = client.post(
        f"/api/v1/decision-snapshots/{snapshot_payload['snapshot_id']}/claim"
    )
    assert claim_response.status_code == 200
    assert claim_response.cookies[GUEST_CAPABILITY_COOKIE]["max-age"] == 0

    correction_response = _post_json(
        client,
        "/api/v1/corrections",
        {
            "offering_id": engineering_ids[0],
            "field_key": bupt_claim.field_key,
            "proposed_source_url": "https://local.test/fixtures/2027/revised-rule",
            "explanation": "本地测试来源显示该资格条件需要按新版本复核。",
        },
    )
    assert correction_response.status_code == 201
    correction_payload = correction_response.json()

    accept_correction(
        correction_id=cast(str, correction_payload["correction_id"]),
        reviewer=reviewer,
        source_document=create_source_document(),
        normalized_value=False,
        original_value="false",
        reviewer_note="已依据本地隔离的 2027 测试来源完成复核。",
        now=timezone.now(),
    )
    outbox = publish_correction(
        correction_id=cast(str, correction_payload["correction_id"]),
        reviewer=reviewer,
        now=timezone.now(),
    )

    first_recomputation = recompute_published_correction(outbox.event_key)
    second_recomputation = recompute_published_correction(outbox.event_key)
    assert first_recomputation == second_recomputation == {
        "affected_runs": 1,
        "created_results": 1,
        "created_snapshot_updates": 1,
    }
    assert JobExecution.objects.filter(event_key=outbox.event_key).count() == 1
    assert ComparisonRunResult.objects.filter(run=original_result.run).count() == 2
    assert SnapshotUpdate.objects.filter(
        outbox_event=outbox,
        old_snapshot=original_snapshot,
        old_result=original_result,
    ).count() == 1

    original_result.refresh_from_db()
    original_snapshot.refresh_from_db()
    assert original_result.result == original_result_payload
    assert original_snapshot.snapshot_hash == original_snapshot_hash
    assert DecisionSnapshot.objects.filter(pk=original_snapshot.pk).count() == 1
    outbox.refresh_from_db()
    assert outbox.processing_state == OutboxEvent.ProcessingState.PROCESSED

    public_payload = json.dumps(
        {
            "scope": scope_response.json(),
            "offerings": offerings_response.json(),
            "assessments": assessments,
            "comparison": comparison_payload,
            "snapshot": snapshot_payload,
            "correction": correction_payload,
        },
        ensure_ascii=False,
    )
    for forbidden in ("synthetic", "test_fixture", "reference_year", "storage_key"):
        assert forbidden not in public_payload
