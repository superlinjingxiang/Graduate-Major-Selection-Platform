from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from advising.factories import (
    approve_claim,
    create_claim,
    create_reviewer,
    create_rule_set,
    create_rule_with_evidence,
    create_source_document,
)
from django.db import close_old_connections, connection
from django.utils import timezone

from gradmatch.accounts.models import User
from gradmatch.advising.models import (
    EligibilityRule,
    EvidenceClaimRevision,
    RuleEvidenceUsage,
    RuleSetRevision,
)
from gradmatch.advising.publication import publish_claim, publish_rule_set
from gradmatch.support.services import (
    accept_correction,
    publish_correction,
    submit_correction,
)


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="requires the native PostgreSQL concurrency backend",
)
@pytest.mark.django_db(transaction=True)
def test_postgres_serializes_corrections_on_the_stable_offering_lock() -> None:
    reviewer = create_reviewer()
    first_claim = create_claim(create_source_document(), field_key="eligibility.first")
    second_claim = create_claim(create_source_document(), field_key="eligibility.second")
    for claim in (first_claim, second_claim):
        approve_claim(claim, reviewer)
        publish_claim(claim_id=claim.pk, reviewer=reviewer, now=timezone.now())

    original = create_rule_set()
    create_rule_with_evidence(original, first_claim)
    second_rule = EligibilityRule.objects.create(
        rule_set=original,
        key="second-rule",
        position=2,
        fact_key="cross_discipline",
        operator=EligibilityRule.Operator.EQUALS,
        expected_value=False,
        failure_reason_code="second_rule_failed",
    )
    RuleEvidenceUsage.objects.create(rule=second_rule, claim=second_claim)
    publish_rule_set(rule_set_id=original.pk, reviewer=reviewer, now=timezone.now())

    correction_ids: list[UUID] = []
    for claim in (first_claim, second_claim):
        correction = submit_correction(
            offering=claim.offering,
            field_key=claim.field_key,
            proposed_source_url="https://yzb.example.edu/2027/concurrent-correction",
            explanation="Concurrent correction regression fixture.",
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
        correction_ids.append(correction.pk)

    barrier = Barrier(2)

    def publish_in_thread(correction_id: UUID) -> int:
        close_old_connections()
        actor = User.objects.get(pk=reviewer.pk)
        barrier.wait(timeout=10)
        event = publish_correction(
            correction_id=correction_id,
            reviewer=actor,
            now=timezone.now(),
        )
        close_old_connections()
        return event.pk

    with ThreadPoolExecutor(max_workers=2) as executor:
        event_ids = list(executor.map(publish_in_thread, correction_ids))

    assert len(set(event_ids)) == 2
    revisions = list(RuleSetRevision.objects.filter(key=original.key))
    assert [revision.revision for revision in revisions] == [3, 2, 1]
    latest_claim_ids = set(
        RuleEvidenceUsage.objects.filter(rule__rule_set=revisions[0]).values_list(
            "claim_id", flat=True
        )
    )
    first_replacement = EvidenceClaimRevision.objects.get(supersedes=first_claim)
    second_replacement = EvidenceClaimRevision.objects.get(supersedes=second_claim)
    assert first_replacement.pk in latest_claim_ids
    assert second_replacement.pk in latest_claim_ids
