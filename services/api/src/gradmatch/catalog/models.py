from __future__ import annotations

from datetime import datetime

from django.db import models
from django.db.models import Q


class CoverageManifest(models.Model):
    key: models.SlugField[str, str] = models.SlugField(max_length=100, unique=True)
    version: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    target_year: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    scope: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField()
    frozen_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()

    class Meta:
        ordering = ["-target_year", "-version"]

    def __str__(self) -> str:
        return self.key


class Institution(models.Model):
    key: models.SlugField[str, str] = models.SlugField(max_length=32, unique=True)
    name: models.CharField[str, str] = models.CharField(max_length=200)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.name


class TaxonomyRevision(models.Model):
    key: models.SlugField[str, str] = models.SlugField(max_length=100, unique=True)
    effective_year: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["-effective_year", "key"]

    def __str__(self) -> str:
        return self.key


class TaxonomyNode(models.Model):
    class LevelType(models.TextChoices):
        ACADEMIC_DISCIPLINE = "academic_discipline", "Academic discipline"
        PROFESSIONAL_FIELD = "professional_field", "Professional field"

    revision: models.ForeignKey[TaxonomyRevision, TaxonomyRevision] = models.ForeignKey(
        TaxonomyRevision,
        on_delete=models.PROTECT,
        related_name="nodes",
    )
    code: models.CharField[str, str] = models.CharField(max_length=16)
    name: models.CharField[str, str] = models.CharField(max_length=200)
    level_type: models.CharField[str, str] = models.CharField(max_length=32, choices=LevelType)
    parent: models.ForeignKey[TaxonomyNode | None, TaxonomyNode | None] = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("revision", "code"),
                name="catalog_taxonomy_node_revision_code_unique",
            )
        ]
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class AnnualOffering(models.Model):
    class DegreeType(models.TextChoices):
        ACADEMIC = "academic", "Academic"
        PROFESSIONAL = "professional", "Professional"

    class StudyMode(models.TextChoices):
        FULL_TIME = "full_time", "Full time"

    class AdmissionPathway(models.TextChoices):
        UNIFIED_EXAM = "unified_exam", "Unified exam"

    class PublicationStatus(models.TextChoices):
        PENDING_PUBLICATION = "pending_publication", "Pending publication"
        CURRENT = "current", "Current"
        CLOSED = "closed", "Closed"

    id: models.CharField[str, str] = models.CharField(primary_key=True, max_length=96)
    target_year: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    institution: models.ForeignKey[Institution, Institution] = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name="annual_offerings",
    )
    taxonomy_node: models.ForeignKey[TaxonomyNode, TaxonomyNode] = models.ForeignKey(
        TaxonomyNode,
        on_delete=models.PROTECT,
        related_name="annual_offerings",
    )
    title: models.CharField[str, str] = models.CharField(max_length=256)
    degree_type: models.CharField[str, str] = models.CharField(max_length=24, choices=DegreeType)
    study_mode: models.CharField[str, str] = models.CharField(max_length=24, choices=StudyMode)
    admission_pathway: models.CharField[str, str] = models.CharField(
        max_length=32,
        choices=AdmissionPathway,
    )
    publication_status: models.CharField[str, str] = models.CharField(
        max_length=32,
        choices=PublicationStatus,
    )

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.institution.name} {self.taxonomy_node.code} {self.title}"


class ManifestEntry(models.Model):
    manifest: models.ForeignKey[CoverageManifest, CoverageManifest] = models.ForeignKey(
        CoverageManifest,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    offering: models.ForeignKey[AnnualOffering, AnnualOffering] = models.ForeignKey(
        AnnualOffering,
        on_delete=models.PROTECT,
        related_name="manifest_entries",
    )
    position: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    engineering_slice: models.BooleanField[bool, bool] = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("manifest", "offering"),
                name="catalog_manifest_entry_offering_unique",
            ),
            models.UniqueConstraint(
                fields=("manifest", "position"),
                name="catalog_manifest_entry_position_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="catalog_manifest_entry_positive_position",
            ),
        ]
        ordering = ["position"]

    def __str__(self) -> str:
        return f"{self.manifest.key}:{self.position}:{self.offering.pk}"
