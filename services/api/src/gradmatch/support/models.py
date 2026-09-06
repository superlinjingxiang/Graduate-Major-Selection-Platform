from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import models
from django.db.models import Q

from gradmatch.accounts.models import User
from gradmatch.advising.models import (
    ComparisonRunResult,
    DecisionSnapshot,
    EvidenceClaimRevision,
    GuestSession,
)
from gradmatch.catalog.models import AnnualOffering


class AppendOnlyEventError(RuntimeError):
    pass


class CorrectionCase(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        ACCEPTED = "accepted", "Accepted"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    id: models.UUIDField[UUID, UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    offering: models.ForeignKey[AnnualOffering, AnnualOffering] = models.ForeignKey(
        AnnualOffering,
        on_delete=models.PROTECT,
        related_name="correction_cases",
    )
    field_key: models.CharField[str, str] = models.CharField(max_length=160)
    proposed_source_url: models.URLField[str, str] = models.URLField(max_length=2048)
    explanation: models.TextField[str, str] = models.TextField()
    status: models.CharField[str, str] = models.CharField(
        max_length=24,
        choices=Status,
        default=Status.SUBMITTED,
    )
    submitter: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="correction_cases",
    )
    guest_session: models.ForeignKey[GuestSession | None, GuestSession | None] = (
        models.ForeignKey(
            GuestSession,
            null=True,
            blank=True,
            on_delete=models.PROTECT,
            related_name="correction_cases",
        )
    )
    accepted_claim: models.ForeignKey[
        EvidenceClaimRevision | None, EvidenceClaimRevision | None
    ] = models.ForeignKey(
        EvidenceClaimRevision,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accepted_correction_cases",
    )
    reviewer_note: models.TextField[str, str] = models.TextField(blank=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(submitter__isnull=False, guest_session__isnull=True)
                    | Q(submitter__isnull=True, guest_session__isnull=False)
                ),
                name="support_correction_exactly_one_submitter",
            )
        ]
        ordering = ["-created_at"]


class AuditEvent(models.Model):
    actor: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="support_audit_events",
    )
    action: models.CharField[str, str] = models.CharField(max_length=80)
    target_type: models.CharField[str, str] = models.CharField(max_length=80)
    target_id: models.CharField[str, str] = models.CharField(max_length=128)
    metadata: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField(
        default=dict
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise AppendOnlyEventError("Audit events are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise AppendOnlyEventError("Audit events are append-only.")


class OutboxEvent(models.Model):
    class ProcessingState(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"

    event_key: models.CharField[str, str] = models.CharField(max_length=160, unique=True)
    event_type: models.CharField[str, str] = models.CharField(max_length=120)
    payload: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField()
    published_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()
    processing_state: models.CharField[str, str] = models.CharField(
        max_length=24,
        choices=ProcessingState,
        default=ProcessingState.PENDING,
    )
    processed_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True,
        blank=True,
    )
    dispatch_attempts: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=0
    )
    last_dispatch_attempt_at: models.DateTimeField[
        datetime | None, datetime | None
    ] = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["published_at", "id"]


class JobExecution(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"

    event_key: models.CharField[str, str] = models.CharField(max_length=160)
    handler_name: models.CharField[str, str] = models.CharField(max_length=160)
    status: models.CharField[str, str] = models.CharField(max_length=24, choices=Status)
    result: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField(
        default=dict
    )
    started_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()
    completed_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("event_key", "handler_name"),
                name="support_job_execution_event_handler_unique",
            )
        ]
        ordering = ["started_at", "id"]


class SnapshotUpdate(models.Model):
    outbox_event: models.ForeignKey[OutboxEvent, OutboxEvent] = models.ForeignKey(
        OutboxEvent,
        on_delete=models.PROTECT,
        related_name="snapshot_updates",
    )
    old_snapshot: models.ForeignKey[DecisionSnapshot, DecisionSnapshot] = models.ForeignKey(
        DecisionSnapshot,
        on_delete=models.PROTECT,
        related_name="updates",
    )
    old_result: models.ForeignKey[ComparisonRunResult, ComparisonRunResult] = models.ForeignKey(
        ComparisonRunResult,
        on_delete=models.PROTECT,
        related_name="snapshot_updates_from",
    )
    new_result: models.ForeignKey[ComparisonRunResult, ComparisonRunResult] = models.ForeignKey(
        ComparisonRunResult,
        on_delete=models.PROTECT,
        related_name="snapshot_updates_to",
    )
    diff: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField()
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("outbox_event", "old_snapshot"),
                name="support_snapshot_update_event_snapshot_unique",
            )
        ]
        ordering = ["created_at", "id"]
