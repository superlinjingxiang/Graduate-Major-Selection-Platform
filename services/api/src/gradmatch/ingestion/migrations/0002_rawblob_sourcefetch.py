from typing import Any

import django.db.models.deletion
from django.db import migrations, models


def migrate_raw_artifacts(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    raw_artifact_model = apps.get_model("ingestion", "RawArtifact")
    raw_blob_model = apps.get_model("ingestion", "RawBlob")
    source_fetch_model = apps.get_model("ingestion", "SourceFetch")
    ingestion_run_model = apps.get_model("ingestion", "IngestionRun")

    for artifact in raw_artifact_model.objects.order_by("id").iterator():
        run_id = artifact.run_id
        if run_id is None:
            run = ingestion_run_model.objects.create(
                source_id=artifact.source_id,
                status="succeeded",
                started_at=artifact.fetched_at,
                finished_at=artifact.fetched_at,
                error_summary="Migrated legacy RawArtifact without an ingestion run.",
            )
            run_id = run.pk

        blob = raw_blob_model.objects.create(
            content_hash=artifact.content_hash,
            storage_key=artifact.storage_key,
            byte_size=0,
            content_type=(artifact.content_type or "")[:128],
        )
        source_fetch_model.objects.create(
            source_id=artifact.source_id,
            run_id=run_id,
            source_url=artifact.source_url,
            requested_at=artifact.fetched_at,
            fetched_at=artifact.fetched_at,
            http_status=None,
            etag="",
            last_modified="",
            status="succeeded",
            blob_id=blob.pk,
            error_summary="",
        )


def restore_raw_artifacts(apps: Any, schema_editor: Any) -> None:
    del schema_editor
    raw_artifact_model = apps.get_model("ingestion", "RawArtifact")
    source_fetch_model = apps.get_model("ingestion", "SourceFetch")

    fetches = (
        source_fetch_model.objects.filter(blob__isnull=False)
        .select_related("blob")
        .order_by("id")
    )
    for fetch in fetches.iterator():
        raw_artifact_model.objects.get_or_create(
            content_hash=fetch.blob.content_hash,
            defaults={
                "source_id": fetch.source_id,
                "run_id": fetch.run_id,
                "storage_key": fetch.blob.storage_key,
                "source_url": fetch.source_url,
                "content_type": fetch.blob.content_type,
                "fetched_at": fetch.fetched_at or fetch.requested_at,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("ingestion", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="RawBlob",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("content_hash", models.CharField(max_length=64, unique=True)),
                ("storage_key", models.CharField(max_length=512, unique=True)),
                ("byte_size", models.PositiveBigIntegerField()),
                ("content_type", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="SourceFetch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("source_url", models.URLField(max_length=2048)),
                ("requested_at", models.DateTimeField()),
                ("fetched_at", models.DateTimeField(blank=True, null=True)),
                ("http_status", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("etag", models.CharField(blank=True, max_length=512)),
                ("last_modified", models.CharField(blank=True, max_length=512)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        max_length=24,
                    ),
                ),
                ("error_summary", models.TextField(blank=True)),
                (
                    "blob",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="ingestion.rawblob",
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fetches",
                        to="ingestion.ingestionrun",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="ingestion.datasource",
                    ),
                ),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.RunPython(migrate_raw_artifacts, restore_raw_artifacts),
        migrations.DeleteModel(name="RawArtifact"),
    ]
