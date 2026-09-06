from __future__ import annotations

from datetime import timedelta
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
from django.utils import timezone

from gradmatch.advising.comparison import create_comparison_run, create_decision_snapshot
from gradmatch.advising.eligibility import canonical_facts_hash
from gradmatch.advising.models import (
    ComparisonRunResult,
    DecisionSnapshot,
    EligibilityRule,
    EvidenceClaimRevision,
    FactSet,
    FactSetRevision,
    PublishedRevisionImmutableError,
    RuleEvidenceUsage,
    RuleSetRevision,
)
from gradmatch.advising.publication import publish_claim, publish_rule_set
from gradmatch.catalog.seed import ENGINEERING_SLICE_OFFERING_IDS
from gradmatch.support import tasks as support_tasks
from gradmatch.support.models import (
    AuditEvent,
    CorrectionCase,
    JobExecution,
    OutboxEvent,
    SnapshotUpdate,
)
from gradmatch.support.services import (
    accept_correction,
    dispatch_pending_outbox_events,
    process_recomputation_event,
    publish_correction,
    select_published_rule_sets_for_update,
    submit_correction,
)


@pytest.mark.django_db
def test_revalidation_lock_query_avoids_distinct_with_select_for_update() -> None:
    claim = create_claim(create_source_document())

    queryset = select_published_rule_sets_for_update(claim)

    assert queryset.query.select_for_update is True
    assert queryset.query.distinct is False


@pytest.mark.django_db
def test_outbox_dispatch_lease_recovers_after_broker_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = timezone.now()
    event = OutboxEvent.objects.create(
        event_key="correction.claim-published:broker-recovery",
        event_type="correction.claim_published",
        payload={},
        published_at=now,
    )

    def fail_to_enqueue(event_key: str) -> None:
        del event_key
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(support_tasks.recompute_published_correction, "delay", fail_to_enqueue)
    assert dispatch_pending_outbox_events(now=now) == 0
    assert dispatch_pending_outbox_events(now=now + timedelta(minutes=1)) == 0

    def enqueue_without_processing(event_key: str) -> str:
        return event_key

    monkeypatch.setattr(
        support_tasks.recompute_published_correction,
        "delay",
        enqueue_without_processing,
    )
    assert dispatch_pending_outbox_events(now=now + timedelta(minutes=6)) == 1
    event.refresh_from_db()
    assert event.dispatch_attempts == 2
    assert event.processing_state == OutboxEvent.ProcessingState.PENDING.value


@pytest.mark.django_db
def test_successive_corrections_clone_one_latest_revision_per_rule_set_family() -> None:
    reviewer = create_reviewer()
    first_claim = create_claim(
        create_source_document(),
        field_key="eligibility.first_rule",
    )
    second_claim = create_claim(
        create_source_document(),
        field_key="eligibility.second_rule",
    )
    for claim in (first_claim, second_claim):
        approve_claim(claim, reviewer)
        publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())

    original_rule_set = create_rule_set()
    create_rule_with_evidence(original_rule_set, first_claim)
    second_rule = EligibilityRule.objects.create(
        rule_set=original_rule_set,
        key="second-rule",
        position=2,
        fact_key="cross_discipline",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=False,
        failure_reason_code="second_rule_failed",
    )
    RuleEvidenceUsage.objects.create(rule=second_rule, claim=second_claim)
    publish_rule_set(
        rule_set_id=original_rule_set.pk,
        reviewer=reviewer,
        now=timezone.now(),
    )

    corrections: list[CorrectionCase] = []
    for claim in (first_claim, second_claim):
        correction = submit_correction(
            offering=claim.offering,
            field_key=claim.field_key,
            proposed_source_url="https://yzb.example.edu/2027/revised-rule",
            explanation="The official evidence changed.",
            submitter=reviewer,
        )
        accept_correction(
            correction_id=correction.pk,
            reviewer=reviewer,
            source_document=create_source_document(),
            normalized_value=False,
            original_value="false",
            reviewer_note="Confirmed.",
            now=timezone.now(),
        )
        corrections.append(correction)

    first_event = publish_correction(
        correction_id=corrections[0].pk,
        reviewer=reviewer,
        now=timezone.now(),
    )
    second_event = publish_correction(
        correction_id=corrections[1].pk,
        reviewer=reviewer,
        now=timezone.now(),
    )

    revisions = list(RuleSetRevision.objects.filter(key=original_rule_set.key))
    assert len(revisions) == 3
    assert [revision.revision for revision in revisions] == [3, 2, 1]
    latest = revisions[0]
    replacement_ids = {
        first_event.payload["replacement_claim_id"],
        second_event.payload["replacement_claim_id"],
    }
    assert set(
        RuleEvidenceUsage.objects.filter(rule__rule_set=latest).values_list(
            "claim_id", flat=True
        )
    ) == replacement_ids


@pytest.mark.django_db
def test_recomputation_is_idempotent_and_preserves_old_results() -> None:
    reviewer = create_reviewer()
    baseline_facts = {
        "target_year": 2027,
        "region": "北京",
        "study_mode": "full_time",
        "admission_pathway": "unified_exam",
    }
    baseline_fact_set = FactSet.objects.create(owner=reviewer)
    baseline_revision = FactSetRevision.objects.create(
        fact_set=baseline_fact_set,
        version=1,
        confirmed_facts=baseline_facts,
        input_hash=canonical_facts_hash(baseline_facts),
    )
    unrelated_result = create_comparison_run(
        fact_revision=baseline_revision,
        offering_ids=ENGINEERING_SLICE_OFFERING_IDS,
        owner=reviewer,
    )

    original_claim = create_claim(create_source_document(), normalized_value=True)
    approve_claim(original_claim, reviewer)
    publish_claim(claim_id=original_claim.pk, reviewer=reviewer, now=timezone.now())
    rule_set = create_rule_set()
    create_rule_with_evidence(rule_set, original_claim)
    publish_rule_set(rule_set_id=rule_set.pk, reviewer=reviewer, now=timezone.now())

    facts = {
        "target_year": 2027,
        "region": "北京",
        "study_mode": "full_time",
        "admission_pathway": "unified_exam",
        "sample_fact": True,
    }
    fact_set = FactSet.objects.create(owner=reviewer)
    fact_revision = FactSetRevision.objects.create(
        fact_set=fact_set,
        version=1,
        confirmed_facts=facts,
        input_hash=canonical_facts_hash(facts),
    )
    original_result = create_comparison_run(
        fact_revision=fact_revision,
        offering_ids=ENGINEERING_SLICE_OFFERING_IDS,
        owner=reviewer,
    )
    original_snapshot = create_decision_snapshot(comparison_result=original_result)
    second_original_snapshot = create_decision_snapshot(comparison_result=original_result)
    original_result_payload = dict(original_result.result)
    original_snapshot_hash = original_snapshot.snapshot_hash

    correction = submit_correction(
        offering=original_claim.offering,
        field_key=original_claim.field_key,
        proposed_source_url="https://yzb.example.edu/2027/revised-rule",
        explanation="A revised official page changes this fact.",
        submitter=reviewer,
    )
    accept_correction(
        correction_id=correction.pk,
        reviewer=reviewer,
        source_document=create_source_document(),
        normalized_value=False,
        original_value="false",
        reviewer_note="Confirmed against the revised source.",
        now=timezone.now(),
    )
    outbox = publish_correction(
        correction_id=correction.pk,
        reviewer=reviewer,
        now=timezone.now(),
    )
    raw_revised_rule_set_ids = outbox.payload["revised_rule_set_ids"]
    assert isinstance(raw_revised_rule_set_ids, list)
    revised_rule_set_ids = cast(list[object], raw_revised_rule_set_ids)
    assert len(revised_rule_set_ids) == 1
    assert isinstance(revised_rule_set_ids[0], int)
    revised_rule_set = RuleSetRevision.objects.get(pk=revised_rule_set_ids[0])
    assert revised_rule_set.revision == rule_set.revision + 1
    assert revised_rule_set.coverage_complete is False
    assert revised_rule_set.status == RuleSetRevision.Status.PUBLISHED.value
    assert RuleEvidenceUsage.objects.filter(
        rule__rule_set=revised_rule_set,
        claim__supersedes=original_claim,
    ).count() == 1

    first_dispatch = dispatch_pending_outbox_events(now=timezone.now())
    second_dispatch = dispatch_pending_outbox_events(now=timezone.now())
    first = process_recomputation_event(event_key=outbox.event_key)
    second = process_recomputation_event(event_key=outbox.event_key)

    assert first_dispatch == 1
    assert second_dispatch == 0
    assert first == second
    assert first == {
        "affected_runs": 1,
        "created_results": 1,
        "created_snapshot_updates": 2,
    }
    assert JobExecution.objects.filter(
        event_key=outbox.event_key,
        handler_name="support.recompute_published_correction",
    ).count() == 1
    assert AuditEvent.objects.filter(
        action="correction.recomputation_succeeded",
        target_type="outbox_event",
        target_id=str(outbox.pk),
    ).count() == 1
    assert ComparisonRunResult.objects.filter(run=original_result.run).count() == 2
    assert ComparisonRunResult.objects.filter(run=unrelated_result.run).count() == 1
    recomputed = ComparisonRunResult.objects.get(run=original_result.run, version=2)
    assert recomputed.trigger_publication_event is not None
    assert recomputed.trigger_publication_event.pk == outbox.payload["publication_event_id"]
    assert recomputed.result_hash != original_result.result_hash
    raw_recomputed_groups = recomputed.result["groups"]
    assert isinstance(raw_recomputed_groups, dict)
    recomputed_groups = cast(dict[str, object], raw_recomputed_groups)
    assert recomputed_groups["eligible_known"] == []
    assert recomputed_groups["ineligible_known"] == []
    raw_needs_confirmation = recomputed_groups["needs_confirmation"]
    assert isinstance(raw_needs_confirmation, list)
    needs_confirmation = cast(list[object], raw_needs_confirmation)
    assert all(isinstance(value, str) for value in needs_confirmation)
    assert set(cast(list[str], needs_confirmation)) == set(ENGINEERING_SLICE_OFFERING_IDS)
    assert SnapshotUpdate.objects.filter(
        outbox_event=outbox,
        old_snapshot=original_snapshot,
        old_result=original_result,
        new_result=recomputed,
    ).count() == 1
    assert SnapshotUpdate.objects.filter(
        outbox_event=outbox,
        old_snapshot=second_original_snapshot,
        old_result=original_result,
        new_result=recomputed,
    ).count() == 1

    original_result.refresh_from_db()
    original_snapshot.refresh_from_db()
    assert original_result.result == original_result_payload
    assert original_snapshot.snapshot_hash == original_snapshot_hash
    original_snapshot.outcome = DecisionSnapshot.Outcome.POSTPONE_APPLICATION
    with pytest.raises(PublishedRevisionImmutableError, match="Decision snapshots"):
        original_snapshot.save()

    outbox.refresh_from_db()
    assert outbox.processing_state == OutboxEvent.ProcessingState.PROCESSED
    assert outbox.processed_at is not None

    latest_snapshot = create_decision_snapshot(comparison_result=recomputed)
    first_replacement = EvidenceClaimRevision.objects.get(supersedes=original_claim)
    second_correction = submit_correction(
        offering=first_replacement.offering,
        field_key=first_replacement.field_key,
        proposed_source_url="https://yzb.example.edu/2027/revised-rule-again",
        explanation="The official evidence changed again.",
        submitter=reviewer,
    )
    accept_correction(
        correction_id=second_correction.pk,
        reviewer=reviewer,
        source_document=create_source_document(),
        normalized_value=True,
        original_value="true",
        reviewer_note="Confirmed the subsequent correction.",
        now=timezone.now(),
    )
    second_outbox = publish_correction(
        correction_id=second_correction.pk,
        reviewer=reviewer,
        now=timezone.now(),
    )

    assert dispatch_pending_outbox_events(now=timezone.now()) == 1
    latest_result = ComparisonRunResult.objects.get(run=original_result.run, version=3)
    assert SnapshotUpdate.objects.filter(outbox_event=second_outbox).count() == 3
    for snapshot in (original_snapshot, second_original_snapshot, latest_snapshot):
        update = SnapshotUpdate.objects.get(
            outbox_event=second_outbox,
            old_snapshot=snapshot,
        )
        assert update.old_result == snapshot.comparison_result
        assert update.new_result == latest_result
