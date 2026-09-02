from __future__ import annotations

import hashlib
import uuid

from django.utils import timezone

from gradmatch.accounts.models import User
from gradmatch.advising.models import (
    EligibilityRule,
    EvidenceClaimRevision,
    ReviewDecision,
    RuleEvidenceUsage,
    RuleSetRevision,
    SourceDocumentRevision,
)
from gradmatch.catalog.models import AnnualOffering, CoverageManifest
from gradmatch.catalog.seed import PILOT_MANIFEST_KEY
from gradmatch.ingestion.models import DataSource, IngestionRun, RawBlob, SourceFetch


def create_reviewer() -> User:
    return User.objects.create_user(
        email=f"reviewer-{uuid.uuid4()}@example.test",
        password="review-password-123",
        is_staff=True,
    )


def create_source_document(
    *,
    data_class: str = SourceDocumentRevision.DataClass.PRODUCTION,
    reference_year: int = 2027,
) -> SourceDocumentRevision:
    unique = uuid.uuid4().hex
    source = DataSource.objects.create(
        key=f"evidence-{unique}",
        name="Evidence fixture",
        base_url=f"https://fixtures.gradmatch.test/{unique}/",
        enabled=True,
        rate_limit_per_minute=10,
    )
    now = timezone.now()
    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRun.Status.SUCCEEDED,
        started_at=now,
        finished_at=now,
    )
    body = f"evidence:{unique}".encode()
    content_hash = hashlib.sha256(body).hexdigest()
    blob = RawBlob.objects.create(
        content_hash=content_hash,
        storage_key=f"ingestion/raw/{content_hash[:2]}/{content_hash}",
        byte_size=len(body),
        content_type="text/html",
    )
    fetch = SourceFetch.objects.create(
        source=source,
        run=run,
        source_url=f"https://fixtures.gradmatch.test/{unique}/document.html",
        requested_at=now,
        fetched_at=now,
        http_status=200,
        status=SourceFetch.Status.SUCCEEDED,
        blob=blob,
    )
    return SourceDocumentRevision.objects.create(
        document_key=f"document-{unique}",
        revision=1,
        source_fetch=fetch,
        title="Evidence document",
        data_class=data_class,
        reference_year=reference_year,
        published_at=now,
        locator="section-1",
    )


def create_claim(
    source_document: SourceDocumentRevision,
    *,
    offering: AnnualOffering | None = None,
    field_key: str = "eligibility.sample_rule",
    normalized_value: object = True,
) -> EvidenceClaimRevision:
    active_offering = offering or AnnualOffering.objects.get(
        pk="ao_2027_bupt_081200_ft_unified_plan01"
    )
    return EvidenceClaimRevision.objects.create(
        offering=active_offering,
        field_key=field_key,
        revision=1,
        normalized_value=normalized_value,
        original_value=str(normalized_value),
        source_document=source_document,
    )


def approve_claim(claim: EvidenceClaimRevision, reviewer: User) -> ReviewDecision:
    return ReviewDecision.objects.create(
        claim=claim,
        reviewer=reviewer,
        outcome=ReviewDecision.Outcome.APPROVED,
        note="Reviewed against the source fixture.",
    )


def create_rule_set(
    *,
    namespace: str = RuleSetRevision.Namespace.PRODUCTION,
    reference_year: int | None = None,
    coverage_complete: bool = True,
) -> RuleSetRevision:
    manifest = CoverageManifest.objects.get(key=PILOT_MANIFEST_KEY)
    return RuleSetRevision.objects.create(
        key=f"rules-{uuid.uuid4().hex}",
        revision=1,
        namespace=namespace,
        target_year=2027,
        reference_year=reference_year,
        manifest=manifest,
        status=RuleSetRevision.Status.DRAFT,
        coverage_complete=coverage_complete,
    )


def create_rule_with_evidence(
    rule_set: RuleSetRevision,
    claim: EvidenceClaimRevision,
    *,
    operator: str = EligibilityRule.Operator.EQUALS,
    expected_value: object = True,
) -> EligibilityRule:
    rule = EligibilityRule.objects.create(
        rule_set=rule_set,
        key="sample-rule",
        position=1,
        fact_key="sample_fact",
        operator=operator,
        expected_value=expected_value,
        failure_reason_code="sample_rule_failed",
    )
    RuleEvidenceUsage.objects.create(rule=rule, claim=claim)
    return rule
