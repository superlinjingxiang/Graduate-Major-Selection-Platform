from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from django.db import transaction
from django.utils import timezone

from .adapters import AdapterRegistry, FetchContext, ParsedItem, default_adapter_registry
from .models import DataSource, IngestionRun, RawBlob, SourceFetch
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
        fetch = SourceFetch.objects.create(
            source=source,
            run=run,
            source_url=source.base_url,
            requested_at=timezone.now(),
            status=SourceFetch.Status.PENDING,
        )
        try:
            result = adapter.fetch(
                FetchContext(
                    source_key=source.key,
                    base_url=source.base_url,
                    rate_limit_per_minute=source.rate_limit_per_minute,
                )
            )
            fetch.source_url = result.source_url
            fetch.fetched_at = result.fetched_at
            fetch.http_status = result.http_status
            fetch.etag = result.etag
            fetch.last_modified = result.last_modified
            blob = _persist_blob(result.body, result.content_type, artifact_store)
            _mark_fetch_succeeded(fetch, blob)
        except Exception as error:
            _mark_fetch_failed(fetch, error)
            raise
        parsed_items = tuple(adapter.parse(result))
        _mark_succeeded(run, parsed_items)
    except Exception as error:
        _mark_failed(run, error)
        raise IngestionExecutionError(f"Ingestion failed for source '{source.key}'.") from error
    return run


def _persist_blob(
    body: bytes,
    content_type: str,
    artifact_store: ArtifactStore,
) -> RawBlob:
    content_hash = hashlib.sha256(body).hexdigest()
    storage_key = f"ingestion/raw/{content_hash[:2]}/{content_hash}.html"
    with transaction.atomic():
        blob, created = RawBlob.objects.get_or_create(
            content_hash=content_hash,
            defaults={
                "storage_key": storage_key,
                "byte_size": len(body),
                "content_type": content_type,
            },
        )
        if created:
            artifact_store.put(blob.storage_key, body, content_type)
    return blob


def _mark_fetch_succeeded(fetch: SourceFetch, blob: RawBlob) -> None:
    fetch.status = SourceFetch.Status.SUCCEEDED
    fetch.blob = blob
    fetch.error_summary = ""
    fetch.save(
        update_fields=(
            "source_url",
            "fetched_at",
            "http_status",
            "etag",
            "last_modified",
            "status",
            "blob",
            "error_summary",
        )
    )


def _mark_fetch_failed(fetch: SourceFetch, error: Exception) -> None:
    fetch.status = SourceFetch.Status.FAILED
    fetch.blob = None
    fetch.error_summary = _sanitize_error(error)
    fetch.save(
        update_fields=(
            "source_url",
            "fetched_at",
            "http_status",
            "etag",
            "last_modified",
            "status",
            "blob",
            "error_summary",
        )
    )


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
