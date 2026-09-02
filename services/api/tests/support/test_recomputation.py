from __future__ import annotations

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
    FactSet,
    FactSetRevision,
    PublishedRevisionImmutableError,
    RuleEvidenceUsage,
    RuleSetRevision,
)
from gradmatch.advising.publication import publish_claim, publish_rule_set
from gradmatch.catalog.seed import ENGINEERING_SLICE_OFFERING_IDS
from gradmatch.support.models import JobExecution, OutboxEvent, SnapshotUpdate
from gradmatch.support.services import (
    accept_correction,
    process_recomputation_event,
    publish_correction,
    submit_correction,
)


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

    first = process_recomputation_event(event_key=outbox.event_key)
    second = process_recomputation_event(event_key=outbox.event_key)

    assert first == second
    assert first == {
        "affected_runs": 1,
        "created_results": 1,
        "created_snapshot_updates": 1,
    }
    assert JobExecution.objects.filter(
        event_key=outbox.event_key,
        handler_name="support.recompute_published_correction",
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
