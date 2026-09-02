from __future__ import annotations

from datetime import datetime

from django.db import models
from django.db.models import Q


class DataSource(models.Model):
    key: models.SlugField[str, str] = models.SlugField(max_length=100, unique=True)
    name: models.CharField[str, str] = models.CharField(max_length=200)
    base_url: models.URLField[str, str] = models.URLField()
    enabled: models.BooleanField[bool, bool] = models.BooleanField(default=True)
    rate_limit_per_minute: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(rate_limit_per_minute__gt=0),
                name="ingestion_data_source_positive_rate_limit",
            )
        ]
        ordering = ["key"]

    def __str__(self) -> str:
        return self.name


class IngestionRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    source: models.ForeignKey[DataSource, DataSource] = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name="runs"
    )
    status: models.CharField[str, str] = models.CharField(
        max_length=16, choices=Status, default=Status.PENDING
    )
    started_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True, blank=True
    )
    finished_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True, blank=True
    )
    records_seen: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(default=0)
    records_accepted: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(default=0)
    error_summary: models.TextField[str, str] = models.TextField(blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.source.key}:{self.status}:{self.pk}"


class RawBlob(models.Model):
    content_hash: models.CharField[str, str] = models.CharField(max_length=64, unique=True)
    storage_key: models.CharField[str, str] = models.CharField(max_length=512, unique=True)
    byte_size: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField()
    content_type: models.CharField[str, str] = models.CharField(max_length=128, blank=True)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.content_hash


class SourceFetch(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    source: models.ForeignKey[DataSource, DataSource] = models.ForeignKey(
        DataSource, on_delete=models.PROTECT
    )
    run: models.ForeignKey[IngestionRun, IngestionRun] = models.ForeignKey(
        IngestionRun,
        on_delete=models.CASCADE,
        related_name="fetches",
    )
    source_url: models.URLField[str, str] = models.URLField(max_length=2048)
    requested_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()
    fetched_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True, blank=True
    )
    http_status: models.PositiveSmallIntegerField[int | None, int | None] = (
        models.PositiveSmallIntegerField(null=True, blank=True)
    )
    etag: models.CharField[str, str] = models.CharField(max_length=512, blank=True)
    last_modified: models.CharField[str, str] = models.CharField(max_length=512, blank=True)
    status: models.CharField[str, str] = models.CharField(max_length=24, choices=Status)
    blob: models.ForeignKey[RawBlob | None, RawBlob | None] = models.ForeignKey(
        RawBlob, null=True, on_delete=models.PROTECT
    )
    error_summary: models.TextField[str, str] = models.TextField(blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.source.key}:{self.status}:{self.pk}"
