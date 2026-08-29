from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .adapters import AdapterRegistry, FetchContext, ParsedItem, default_adapter_registry
from .models import DataSource, IngestionRun, RawArtifact
from .storage import ArtifactStore


class UnknownDataSourceError(ValueError):
    pass


class DisabledDataSourceError(ValueError):
    pass


class IngestionExecutionError(RuntimeError):
    pass


SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|secret|token|authorization)\s*[=:]\s*[^\s,;]+"
)


def execute_source(
    source_key: str,
    *,
    artifact_store: ArtifactStore,
    registry: AdapterRegistry | None = None,
) -> IngestionRun:
    try:
        source = DataSource.objects.get(key=source_key)
    except DataSource.DoesNotExist as error:
        raise UnknownDataSourceError(f"Unknown data source '{source_key}'.") from error

    if not source.enabled:
        run = IngestionRun.objects.create(source=source, status=IngestionRun.Status.FAILED)
        _mark_failed(run, DisabledDataSourceError("Source is disabled."))
        raise DisabledDataSourceError(f"Source '{source.key}' is disabled.")

    active_registry = registry or default_adapter_registry
    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRun.Status.RUNNING,
        started_at=timezone.now(),
    )
    try:
        adapter = active_registry.get(source.key)
        result = adapter.fetch(
            FetchContext(
                source_key=source.key,
                base_url=source.base_url,
                rate_limit_per_minute=source.rate_limit_per_minute,
            )
        )
        _persist_artifact(
            source,
            run,
            result.body,
            result.source_url,
            result.content_type,
            result.fetched_at,
            artifact_store,
        )
        parsed_items = tuple(adapter.parse(result))
        _mark_succeeded(run, parsed_items)
    except Exception as error:
        _mark_failed(run, error)
        raise IngestionExecutionError(f"Ingestion failed for source '{source.key}'.") from error
    return run


def _persist_artifact(
    source: DataSource,
    run: IngestionRun,
    body: bytes,
    source_url: str,
    content_type: str,
    fetched_at: datetime,
    artifact_store: ArtifactStore,
) -> RawArtifact:
    content_hash = hashlib.sha256(body).hexdigest()
    storage_key = f"ingestion/raw/{content_hash[:2]}/{content_hash}.html"
    with transaction.atomic():
        artifact, created = RawArtifact.objects.get_or_create(
            content_hash=content_hash,
            defaults={
                "source": source,
                "run": run,
                "storage_key": storage_key,
                "source_url": source_url,
                "content_type": content_type,
                "fetched_at": fetched_at,
            },
        )
        if created:
            artifact_store.put(storage_key, body, content_type)
    return artifact


def _mark_succeeded(run: IngestionRun, parsed_items: Iterable[ParsedItem]) -> None:
    item_count = sum(1 for _ in parsed_items)
    run.status = IngestionRun.Status.SUCCEEDED
    run.records_seen = item_count
    run.records_accepted = item_count
    run.finished_at = timezone.now()
    run.error_summary = ""
    run.save(
        update_fields=("status", "records_seen", "records_accepted", "finished_at", "error_summary")
    )


def _mark_failed(run: IngestionRun, error: Exception) -> None:
    run.status = IngestionRun.Status.FAILED
    run.finished_at = timezone.now()
    run.error_summary = _sanitize_error(error)
    run.save(update_fields=("status", "finished_at", "error_summary"))


def _sanitize_error(error: Exception) -> str:
    compact_message = " ".join(str(error).split())
    redacted_message = SENSITIVE_VALUE_PATTERN.sub(r"\1=<redacted>", compact_message)
    return f"{type(error).__name__}: {redacted_message}"[:500]
