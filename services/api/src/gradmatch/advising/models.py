from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import models
from django.db.models import Q

from gradmatch.accounts.models import User
from gradmatch.catalog.models import AnnualOffering, CoverageManifest
from gradmatch.ingestion.models import SourceFetch


class PublishedRevisionImmutableError(RuntimeError):
    pass


class SourceDocumentRevision(models.Model):
    class DataClass(models.TextChoices):
        PRODUCTION = "production", "Production"
        SYNTHETIC = "synthetic", "Synthetic"
        HISTORICAL_REFERENCE = "historical_reference", "Historical reference"

    document_key: models.SlugField[str, str] = models.SlugField(max_length=120)
    revision: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    source_fetch: models.ForeignKey[SourceFetch, SourceFetch] = models.ForeignKey(
        SourceFetch,
        on_delete=models.PROTECT,
        related_name="document_revisions",
    )
    title: models.CharField[str, str] = models.CharField(max_length=300)
    data_class: models.CharField[str, str] = models.CharField(max_length=32, choices=DataClass)
    reference_year: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    published_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()
    locator: models.CharField[str, str] = models.CharField(max_length=500, blank=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("document_key", "revision"),
                name="advising_source_document_key_revision_unique",
            )
        ]
        ordering = ["document_key", "-revision"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None and PublicationEvent.objects.filter(
            claim__source_document=self
        ).exists():
            persisted = SourceDocumentRevision.objects.get(pk=self.pk)
            immutable_values = (
                persisted.document_key == self.document_key,
                persisted.revision == self.revision,
                persisted.source_fetch == self.source_fetch,
                persisted.title == self.title,
                persisted.data_class == self.data_class,
                persisted.reference_year == self.reference_year,
                persisted.published_at == self.published_at,
                persisted.locator == self.locator,
            )
            if not all(immutable_values):
                raise PublishedRevisionImmutableError(
                    "A published source document is immutable; create a new revision."
                )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.document_key}:r{self.revision}"


class EvidenceClaimRevision(models.Model):
    claim_key: models.UUIDField[UUID, UUID] = models.UUIDField(default=uuid.uuid4)
    revision: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    supersedes: models.OneToOneField[
        EvidenceClaimRevision | None, EvidenceClaimRevision | None
    ] = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="superseded_by",
    )
    offering: models.ForeignKey[AnnualOffering, AnnualOffering] = models.ForeignKey(
        AnnualOffering,
        on_delete=models.PROTECT,
        related_name="evidence_claim_revisions",
    )
    field_key: models.CharField[str, str] = models.CharField(max_length=160)
    normalized_value: models.JSONField[object, object] = models.JSONField()
    original_value: models.TextField[str, str] = models.TextField()
    source_document: models.ForeignKey[SourceDocumentRevision, SourceDocumentRevision] = (
        models.ForeignKey(
            SourceDocumentRevision,
            on_delete=models.PROTECT,
            related_name="claim_revisions",
        )
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("claim_key", "revision"),
                name="advising_evidence_claim_key_revision_unique",
            )
        ]
        ordering = ["claim_key", "-revision"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None and PublicationEvent.objects.filter(claim=self).exists():
            persisted = EvidenceClaimRevision.objects.get(pk=self.pk)
            immutable_values = (
                persisted.claim_key == self.claim_key,
                persisted.revision == self.revision,
                persisted.supersedes == self.supersedes,
                persisted.offering == self.offering,
                persisted.field_key == self.field_key,
                persisted.normalized_value == self.normalized_value,
                persisted.original_value == self.original_value,
                persisted.source_document == self.source_document,
            )
            if not all(immutable_values):
                raise PublishedRevisionImmutableError(
                    "A published evidence claim is immutable; create a new revision."
                )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.claim_key}:r{self.revision}:{self.field_key}"


class ReviewDecision(models.Model):
    class Outcome(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    claim: models.ForeignKey[EvidenceClaimRevision, EvidenceClaimRevision] = models.ForeignKey(
        EvidenceClaimRevision,
        on_delete=models.PROTECT,
        related_name="review_decisions",
    )
    reviewer: models.ForeignKey[User, User] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidence_review_decisions",
    )
    outcome: models.CharField[str, str] = models.CharField(max_length=16, choices=Outcome)
    note: models.TextField[str, str] = models.TextField(blank=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class PublicationEvent(models.Model):
    claim: models.OneToOneField[EvidenceClaimRevision, EvidenceClaimRevision] = (
        models.OneToOneField(
            EvidenceClaimRevision,
            on_delete=models.PROTECT,
            related_name="publication_event",
        )
    )
    reviewer: models.ForeignKey[User, User] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evidence_publication_events",
    )
    published_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()

    class Meta:
        ordering = ["-published_at", "-id"]


class RuleSetRevision(models.Model):
    class Namespace(models.TextChoices):
        PRODUCTION = "production", "Production"
        TEST_FIXTURE = "test_fixture", "Test fixture"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    key: models.SlugField[str, str] = models.SlugField(max_length=120)
    revision: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    namespace: models.CharField[str, str] = models.CharField(max_length=24, choices=Namespace)
    target_year: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    reference_year: models.PositiveSmallIntegerField[int | None, int | None] = (
        models.PositiveSmallIntegerField(null=True, blank=True)
    )
    manifest: models.ForeignKey[CoverageManifest, CoverageManifest] = models.ForeignKey(
        CoverageManifest,
        on_delete=models.PROTECT,
        related_name="rule_set_revisions",
    )
    status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=Status,
        default=Status.DRAFT,
    )
    coverage_complete: models.BooleanField[bool, bool] = models.BooleanField(default=False)
    published_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True,
        blank=True,
    )
    published_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="published_rule_set_revisions",
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("key", "revision"),
                name="advising_rule_set_key_revision_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(namespace="production", reference_year__isnull=True)
                    | Q(namespace="test_fixture", reference_year__isnull=False)
                ),
                name="advising_rule_set_namespace_reference_year_valid",
            ),
        ]
        ordering = ["key", "-revision"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            persisted = RuleSetRevision.objects.get(pk=self.pk)
            if persisted.status == self.Status.PUBLISHED.value:
                immutable_values = (
                    persisted.key == self.key,
                    persisted.revision == self.revision,
                    persisted.namespace == self.namespace,
                    persisted.target_year == self.target_year,
                    persisted.reference_year == self.reference_year,
                    persisted.manifest == self.manifest,
                    persisted.status == self.status,
                    persisted.coverage_complete == self.coverage_complete,
                    persisted.published_at == self.published_at,
                    persisted.published_by == self.published_by,
                )
                if not all(immutable_values):
                    raise PublishedRevisionImmutableError(
                        "A published rule set is immutable; create a new revision."
                    )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.key}:r{self.revision}:{self.namespace}"


class EligibilityRule(models.Model):
    class Operator(models.TextChoices):
        EQUALS = "equals", "Equals"
        IN = "in", "In"
        GTE = "gte", "Greater than or equal"
        IS_TRUE = "is_true", "Is true"

    rule_set: models.ForeignKey[RuleSetRevision, RuleSetRevision] = models.ForeignKey(
        RuleSetRevision,
        on_delete=models.PROTECT,
        related_name="rules",
    )
    key: models.SlugField[str, str] = models.SlugField(max_length=120)
    position: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    fact_key: models.CharField[str, str] = models.CharField(max_length=160)
    operator: models.CharField[str, str] = models.CharField(max_length=16, choices=Operator)
    expected_value: models.JSONField[object, object] = models.JSONField()
    failure_reason_code: models.SlugField[str, str] = models.SlugField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("rule_set", "key"),
                name="advising_eligibility_rule_set_key_unique",
            ),
            models.UniqueConstraint(
                fields=("rule_set", "position"),
                name="advising_eligibility_rule_set_position_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="advising_eligibility_rule_positive_position",
            ),
        ]
        ordering = ["position"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if RuleSetRevision.objects.filter(
            pk=self.rule_set.pk,
            status=RuleSetRevision.Status.PUBLISHED.value,
        ).exists():
            if self.pk is None:
                raise PublishedRevisionImmutableError(
                    "Rules cannot be added to a published rule set."
                )
            persisted = EligibilityRule.objects.get(pk=self.pk)
            immutable_values = (
                persisted.rule_set == self.rule_set,
                persisted.key == self.key,
                persisted.position == self.position,
                persisted.fact_key == self.fact_key,
                persisted.operator == self.operator,
                persisted.expected_value == self.expected_value,
                persisted.failure_reason_code == self.failure_reason_code,
            )
            if not all(immutable_values):
                raise PublishedRevisionImmutableError(
                    "A rule in a published rule set is immutable; create a new revision."
                )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        if RuleSetRevision.objects.filter(
            pk=self.rule_set.pk,
            status=RuleSetRevision.Status.PUBLISHED.value,
        ).exists():
            raise PublishedRevisionImmutableError(
                "A rule in a published rule set cannot be deleted."
            )
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.rule_set.key}:{self.key}"


class RuleEvidenceUsage(models.Model):
    rule: models.ForeignKey[EligibilityRule, EligibilityRule] = models.ForeignKey(
        EligibilityRule,
        on_delete=models.PROTECT,
        related_name="evidence_usages",
    )
    claim: models.ForeignKey[EvidenceClaimRevision, EvidenceClaimRevision] = models.ForeignKey(
        EvidenceClaimRevision,
        on_delete=models.PROTECT,
        related_name="rule_evidence_usages",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("rule", "claim"),
                name="advising_rule_evidence_usage_unique",
            )
        ]
        ordering = ["rule", "claim"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if RuleSetRevision.objects.filter(
            pk=self.rule.rule_set.pk,
            status=RuleSetRevision.Status.PUBLISHED.value,
        ).exists():
            raise PublishedRevisionImmutableError(
                "Evidence usages in a published rule set are immutable."
            )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        if RuleSetRevision.objects.filter(
            pk=self.rule.rule_set.pk,
            status=RuleSetRevision.Status.PUBLISHED.value,
        ).exists():
            raise PublishedRevisionImmutableError(
                "Evidence usages in a published rule set cannot be deleted."
            )
        return super().delete(*args, **kwargs)


class GuestSession(models.Model):
    id: models.UUIDField[UUID, UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    token_digest: models.CharField[str, str] = models.CharField(
        max_length=64,
        unique=True,
    )
    expires_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()
    owner: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="claimed_guest_sessions",
    )
    claimed_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True,
        blank=True,
    )
    revoked_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class FactSet(models.Model):
    id: models.UUIDField[UUID, UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    owner: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="fact_sets",
    )
    guest_session: models.ForeignKey[GuestSession | None, GuestSession | None] = (
        models.ForeignKey(
            GuestSession,
            null=True,
            blank=True,
            on_delete=models.PROTECT,
            related_name="fact_sets",
        )
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(owner__isnull=True) | Q(guest_session__isnull=True),
                name="advising_fact_set_single_owner_boundary",
            )
        ]
        ordering = ["-created_at"]


class FactSetRevision(models.Model):
    fact_set: models.ForeignKey[FactSet, FactSet] = models.ForeignKey(
        FactSet,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    version: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    confirmed_facts: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField()
    input_hash: models.CharField[str, str] = models.CharField(max_length=64)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("fact_set", "version"),
                name="advising_fact_set_revision_version_unique",
            )
        ]
        ordering = ["fact_set", "-version"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            persisted = FactSetRevision.objects.get(pk=self.pk)
            immutable_values = (
                persisted.fact_set == self.fact_set,
                persisted.version == self.version,
                persisted.confirmed_facts == self.confirmed_facts,
                persisted.input_hash == self.input_hash,
            )
            if not all(immutable_values):
                raise PublishedRevisionImmutableError(
                    "A fact set revision is immutable; create the next version."
                )
        super().save(*args, **kwargs)


class EligibilityAssessment(models.Model):
    class Status(models.TextChoices):
        ELIGIBLE_KNOWN = "eligible_known", "Eligible known"
        INELIGIBLE_KNOWN = "ineligible_known", "Ineligible known"
        NEEDS_CONFIRMATION = "needs_confirmation", "Needs confirmation"

    offering: models.ForeignKey[AnnualOffering, AnnualOffering] = models.ForeignKey(
        AnnualOffering,
        on_delete=models.PROTECT,
        related_name="eligibility_assessments",
    )
    fact_revision: models.ForeignKey[FactSetRevision, FactSetRevision] = models.ForeignKey(
        FactSetRevision,
        on_delete=models.PROTECT,
        related_name="eligibility_assessments",
    )
    rule_set: models.ForeignKey[RuleSetRevision | None, RuleSetRevision | None] = (
        models.ForeignKey(
            RuleSetRevision,
            null=True,
            blank=True,
            on_delete=models.PROTECT,
            related_name="eligibility_assessments",
        )
    )
    status: models.CharField[str, str] = models.CharField(max_length=32, choices=Status)
    reasons: models.JSONField[list[dict[str, object]], list[dict[str, object]]] = models.JSONField()
    input_hash: models.CharField[str, str] = models.CharField(max_length=64, db_index=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            persisted = EligibilityAssessment.objects.get(pk=self.pk)
            immutable_values = (
                persisted.offering == self.offering,
                persisted.fact_revision == self.fact_revision,
                persisted.rule_set == self.rule_set,
                persisted.status == self.status,
                persisted.reasons == self.reasons,
                persisted.input_hash == self.input_hash,
            )
            if not all(immutable_values):
                raise PublishedRevisionImmutableError(
                    "Eligibility assessments are immutable; create a new assessment."
                )
        super().save(*args, **kwargs)


class ComparisonRun(models.Model):
    id: models.UUIDField[UUID, UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    fact_revision: models.ForeignKey[FactSetRevision, FactSetRevision] = models.ForeignKey(
        FactSetRevision,
        on_delete=models.PROTECT,
        related_name="comparison_runs",
    )
    manifest: models.ForeignKey[CoverageManifest, CoverageManifest] = models.ForeignKey(
        CoverageManifest,
        on_delete=models.PROTECT,
        related_name="comparison_runs",
    )
    selected_offering_ids: models.JSONField[list[str], list[str]] = models.JSONField()
    owner: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="comparison_runs",
    )
    guest_session: models.ForeignKey[GuestSession | None, GuestSession | None] = (
        models.ForeignKey(
            GuestSession,
            null=True,
            blank=True,
            on_delete=models.PROTECT,
            related_name="comparison_runs",
        )
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(owner__isnull=False, guest_session__isnull=True)
                    | Q(owner__isnull=True, guest_session__isnull=False)
                ),
                name="advising_comparison_run_exactly_one_owner",
            )
        ]
        ordering = ["-created_at"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            persisted = ComparisonRun.objects.get(pk=self.pk)
            immutable_values = (
                persisted.fact_revision == self.fact_revision,
                persisted.manifest == self.manifest,
                persisted.selected_offering_ids == self.selected_offering_ids,
                persisted.owner == self.owner,
                persisted.guest_session == self.guest_session,
            )
            if not all(immutable_values):
                raise PublishedRevisionImmutableError(
                    "A comparison run is immutable; create a new run."
                )
        super().save(*args, **kwargs)


class ComparisonRunResult(models.Model):
    run: models.ForeignKey[ComparisonRun, ComparisonRun] = models.ForeignKey(
        ComparisonRun,
        on_delete=models.PROTECT,
        related_name="results",
    )
    version: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    result: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField()
    result_hash: models.CharField[str, str] = models.CharField(max_length=64, db_index=True)
    trigger_publication_event: models.ForeignKey[
        PublicationEvent | None, PublicationEvent | None
    ] = models.ForeignKey(
        PublicationEvent,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="triggered_comparison_results",
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("run", "version"),
                name="advising_comparison_result_run_version_unique",
            )
        ]
        ordering = ["run", "-version"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            persisted = ComparisonRunResult.objects.get(pk=self.pk)
            immutable_values = (
                persisted.run == self.run,
                persisted.version == self.version,
                persisted.result == self.result,
                persisted.result_hash == self.result_hash,
                persisted.trigger_publication_event == self.trigger_publication_event,
            )
            if not all(immutable_values):
                raise PublishedRevisionImmutableError(
                    "Comparison results are immutable; create the next result version."
                )
        super().save(*args, **kwargs)


class ComparisonAssessmentUsage(models.Model):
    result: models.ForeignKey[ComparisonRunResult, ComparisonRunResult] = models.ForeignKey(
        ComparisonRunResult,
        on_delete=models.PROTECT,
        related_name="assessment_usages",
    )
    assessment: models.ForeignKey[EligibilityAssessment, EligibilityAssessment] = (
        models.ForeignKey(
            EligibilityAssessment,
            on_delete=models.PROTECT,
            related_name="comparison_usages",
        )
    )
    position: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("result", "assessment"),
                name="advising_comparison_assessment_unique",
            ),
            models.UniqueConstraint(
                fields=("result", "position"),
                name="advising_comparison_assessment_position_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="advising_comparison_assessment_positive_position",
            ),
        ]
        ordering = ["position"]


class DecisionSnapshot(models.Model):
    class Outcome(models.TextChoices):
        SHORTLIST_READY = "shortlist_ready", "Shortlist ready"
        NO_SUITABLE_OFFERING = "no_suitable_offering", "No suitable offering"
        AWAITING_OFFICIAL_INFORMATION = (
            "awaiting_official_information",
            "Awaiting official information",
        )
        POSTPONE_APPLICATION = "postpone_application", "Postpone application"

    id: models.UUIDField[UUID, UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    comparison_result: models.ForeignKey[ComparisonRunResult, ComparisonRunResult] = (
        models.ForeignKey(
            ComparisonRunResult,
            on_delete=models.PROTECT,
            related_name="decision_snapshots",
        )
    )
    outcome: models.CharField[str, str] = models.CharField(max_length=40, choices=Outcome)
    retained: models.JSONField[list[str], list[str]] = models.JSONField()
    excluded: models.JSONField[list[str], list[str]] = models.JSONField()
    deferred: models.JSONField[list[str], list[str]] = models.JSONField()
    user_confirmed_reasons: models.JSONField[list[str], list[str]] = models.JSONField(default=list)
    key_unknowns: models.JSONField[list[str], list[str]] = models.JSONField(default=list)
    next_actions: models.JSONField[list[str], list[str]] = models.JSONField(default=list)
    revisit_date: models.DateField[date | None, date | None] = models.DateField(
        null=True,
        blank=True,
    )
    snapshot_hash: models.CharField[str, str] = models.CharField(max_length=64, db_index=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            persisted = DecisionSnapshot.objects.get(pk=self.pk)
            immutable_values = (
                persisted.comparison_result == self.comparison_result,
                persisted.outcome == self.outcome,
                persisted.retained == self.retained,
                persisted.excluded == self.excluded,
                persisted.deferred == self.deferred,
                persisted.user_confirmed_reasons == self.user_confirmed_reasons,
                persisted.key_unknowns == self.key_unknowns,
                persisted.next_actions == self.next_actions,
                persisted.revisit_date == self.revisit_date,
                persisted.snapshot_hash == self.snapshot_hash,
            )
            if not all(immutable_values):
                raise PublishedRevisionImmutableError(
                    "Decision snapshots are immutable; create a new snapshot."
                )
        super().save(*args, **kwargs)
