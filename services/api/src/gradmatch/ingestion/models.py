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


class RawArtifact(models.Model):
    source: models.ForeignKey[DataSource, DataSource] = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name="raw_artifacts"
    )
    run: models.ForeignKey[IngestionRun | None, IngestionRun | None] = models.ForeignKey(
        IngestionRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="raw_artifacts",
    )
    content_hash: models.CharField[str, str] = models.CharField(max_length=64, unique=True)
    storage_key: models.CharField[str, str] = models.CharField(max_length=512)
    source_url: models.URLField[str, str] = models.URLField()
    content_type: models.CharField[str, str] = models.CharField(max_length=255)
    fetched_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.content_hash
