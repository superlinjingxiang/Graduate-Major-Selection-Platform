from __future__ import annotations

import hashlib
import socket
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import pytest
from django.conf import settings
from django.contrib import admin
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from gradmatch.ingestion.adapters import (
    AdapterRegistry,
    DuplicateAdapterKeyError,
    FetchContext,
    FetchResult,
    ParsedItem,
    SmokeFixtureAdapter,
    UnknownAdapterKeyError,
    default_adapter_registry,
)
from gradmatch.ingestion.models import DataSource, IngestionRun, RawBlob, SourceFetch
from gradmatch.ingestion.runner import (
    DisabledDataSourceError,
    IngestionExecutionError,
    UnknownDataSourceError,
    execute_source,
)
from gradmatch.ingestion.storage import InMemoryArtifactStore
from gradmatch.ingestion.tasks import run_source

FIXTURE_URL = "https://fixtures.gradmatch.test/sample-source.html"


def create_source(**overrides: object) -> DataSource:
    values: dict[str, object] = {
        "key": SmokeFixtureAdapter.key,
        "name": "Smoke fixture",
        "base_url": FIXTURE_URL,
        "enabled": True,
        "rate_limit_per_minute": 30,
    }
    values.update(overrides)
    return DataSource.objects.create(**values)


def test_adapter_registry_rejects_duplicate_and_unknown_keys() -> None:
    registry = AdapterRegistry()
    adapter = SmokeFixtureAdapter()

    registry.register(adapter)

    with pytest.raises(DuplicateAdapterKeyError, match=adapter.key):
        registry.register(adapter)
    with pytest.raises(UnknownAdapterKeyError, match="unknown-source"):
        registry.get("unknown-source")


def test_ingestion_models_are_available_in_django_admin() -> None:
    assert admin.site.is_registered(DataSource)
    assert admin.site.is_registered(IngestionRun)
    assert admin.site.is_registered(RawBlob)
    assert admin.site.is_registered(SourceFetch)


@pytest.mark.django_db
def test_data_source_requires_a_positive_rate_limit() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        create_source(rate_limit_per_minute=0)


@pytest.mark.django_db
def test_disabled_source_is_refused_and_recorded() -> None:
    source = create_source(enabled=False)

    with pytest.raises(DisabledDataSourceError, match=source.key):
        execute_source(source.key, artifact_store=InMemoryArtifactStore())

    run = IngestionRun.objects.get(source=source)
    assert run.status == IngestionRun.Status.FAILED
    assert run.error_summary == "DisabledDataSourceError: Source is disabled."
    assert RawBlob.objects.count() == 0
    assert SourceFetch.objects.count() == 0


@pytest.mark.django_db
def test_unknown_source_is_refused_clearly() -> None:
    with pytest.raises(UnknownDataSourceError, match="does-not-exist"):
        execute_source("does-not-exist", artifact_store=InMemoryArtifactStore())

    assert IngestionRun.objects.count() == 0


@pytest.mark.django_db
def test_smoke_fixture_run_persists_raw_bytes_and_counts_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = create_source()
    store = InMemoryArtifactStore()
    monkeypatch.setattr(socket, "create_connection", _fail_network_connection)

    run = execute_source(source.key, artifact_store=store)

    expected_body = (Path(__file__).parent / "fixtures" / "sample-source.html").read_bytes()
    expected_hash = hashlib.sha256(expected_body).hexdigest()
    blob = RawBlob.objects.get()
    fetch = SourceFetch.objects.get()
    assert run.status == IngestionRun.Status.SUCCEEDED
    assert run.records_seen == 2
    assert run.records_accepted == 2
    assert run.finished_at is not None
    assert blob.content_hash == expected_hash
    assert blob.byte_size == len(expected_body)
    assert blob.content_type == "text/html"
    assert fetch.source == source
    assert fetch.run == run
    assert fetch.source_url == FIXTURE_URL
    assert fetch.fetched_at is not None
    assert fetch.requested_at <= fetch.fetched_at
    assert fetch.status == "succeeded"
    assert fetch.http_status is None
    assert fetch.etag == ""
    assert fetch.last_modified == ""
    assert fetch.blob == blob
    assert store.objects[blob.storage_key].body == expected_body
    assert store.objects[blob.storage_key].content_type == "text/html"


@pytest.mark.django_db
def test_source_fetch_retains_response_metadata() -> None:
    source = create_source(key=MetadataAdapter.key)
    registry = AdapterRegistry()
    registry.register(MetadataAdapter())

    run = execute_source(
        source.key,
        artifact_store=InMemoryArtifactStore(),
        registry=registry,
    )

    fetch = SourceFetch.objects.get(run=run)
    assert fetch.source_url == "https://fixtures.gradmatch.test/redirected.html"
    assert fetch.fetched_at is not None
    assert fetch.requested_at <= fetch.fetched_at
    assert fetch.http_status == 200
    assert fetch.etag == '"fixture-v1"'
    assert fetch.last_modified == "Wed, 02 Sep 2026 08:00:00 GMT"
    assert fetch.status == "succeeded"
    assert fetch.blob is not None


@pytest.mark.django_db
def test_identical_raw_content_is_stored_once_across_runs() -> None:
    source = create_source()
    store = InMemoryArtifactStore()

    first_run = execute_source(source.key, artifact_store=store)
    second_run = execute_source(source.key, artifact_store=store)

    blob = RawBlob.objects.get()
    fetches = list(SourceFetch.objects.order_by("id"))
    assert RawBlob.objects.count() == 1
    assert SourceFetch.objects.count() == 2
    assert len(store.objects) == 1
    assert [fetch.run for fetch in fetches] == [first_run, second_run]
    for fetch in fetches:
        assert fetch.blob == blob
        assert fetch.source_url == FIXTURE_URL
        assert fetch.fetched_at is not None
        assert fetch.requested_at <= fetch.fetched_at
        assert fetch.status == "succeeded"
    assert second_run.status == IngestionRun.Status.SUCCEEDED
    assert second_run.records_seen == 2


@pytest.mark.django_db
def test_failed_access_creates_a_source_fetch_without_a_blob() -> None:
    source = create_source(key="fetch-failing-fixture")
    registry = AdapterRegistry()
    registry.register(FetchFailingAdapter())
    store = InMemoryArtifactStore()

    with pytest.raises(IngestionExecutionError, match="fetch-failing-fixture"):
        execute_source(source.key, artifact_store=store, registry=registry)

    run = IngestionRun.objects.get(source=source)
    fetch = SourceFetch.objects.get(run=run)
    assert run.status == IngestionRun.Status.FAILED
    assert fetch.source == source
    assert fetch.source_url == source.base_url
    assert fetch.requested_at is not None
    assert fetch.fetched_at is None
    assert fetch.status == "failed"
    assert fetch.blob is None
    assert "very-secret" not in fetch.error_summary
    assert "\n" not in fetch.error_summary
    assert RawBlob.objects.count() == 0
    assert store.objects == {}


@pytest.mark.django_db
def test_storage_failure_retains_completed_response_metadata_without_a_blob() -> None:
    source = create_source(key=MetadataAdapter.key)
    registry = AdapterRegistry()
    registry.register(MetadataAdapter())

    with pytest.raises(IngestionExecutionError, match=MetadataAdapter.key):
        execute_source(
            source.key,
            artifact_store=FailingArtifactStore(),
            registry=registry,
        )

    fetch = SourceFetch.objects.get(source=source)
    assert fetch.status == "failed"
    assert fetch.source_url == "https://fixtures.gradmatch.test/redirected.html"
    assert fetch.fetched_at is not None
    assert fetch.http_status == 200
    assert fetch.etag == '"fixture-v1"'
    assert fetch.last_modified == "Wed, 02 Sep 2026 08:00:00 GMT"
    assert fetch.blob is None
    assert RawBlob.objects.count() == 0


@pytest.mark.django_db
def test_parse_failure_marks_run_failed_and_sanitizes_the_error() -> None:
    source = create_source(key="failing-fixture")
    registry = AdapterRegistry()
    registry.register(FailingAdapter())
    store = InMemoryArtifactStore()

    with pytest.raises(IngestionExecutionError, match="failing-fixture"):
        execute_source(source.key, artifact_store=store, registry=registry)

    run = IngestionRun.objects.get(source=source)
    assert run.status == IngestionRun.Status.FAILED
    assert run.finished_at is not None
    assert run.error_summary is not None
    assert "very-secret" not in run.error_summary
    assert "\n" not in run.error_summary
    assert RawBlob.objects.count() == 1
    fetch = SourceFetch.objects.get(run=run)
    assert fetch.status == "succeeded"
    assert fetch.blob is not None
    assert fetch.error_summary == ""
    assert len(store.objects) == 1


@pytest.mark.django_db
def test_default_registry_executes_the_smoke_adapter_without_network_access() -> None:
    source = create_source()

    run = execute_source(source.key, artifact_store=InMemoryArtifactStore())

    assert default_adapter_registry.get(source.key).key == SmokeFixtureAdapter.key
    assert run.status == IngestionRun.Status.SUCCEEDED


def test_celery_uses_redis_and_is_eager_in_tests() -> None:
    assert settings.CELERY_BROKER_URL == settings.REDIS_URL
    assert settings.CELERY_RESULT_BACKEND == settings.REDIS_URL
    assert settings.CELERY_TASK_ALWAYS_EAGER is True


@pytest.mark.django_db
def test_named_celery_task_runs_the_smoke_source_eagerly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = create_source()
    store = InMemoryArtifactStore()
    monkeypatch.setattr("gradmatch.ingestion.tasks.get_artifact_store", lambda: store)

    result = cast(Any, run_source.delay(source.key))  # pyright: ignore[reportCallIssue]

    run = IngestionRun.objects.get(pk=cast(int, result.get()))
    assert run_source.name == "ingestion.run_source"
    assert run.status == IngestionRun.Status.SUCCEEDED
    assert len(store.objects) == 1


@pytest.mark.django_db(transaction=True)
def test_migration_preserves_existing_raw_artifacts_before_removing_the_old_model() -> None:
    old_target = [("ingestion", "0001_initial")]
    new_target = [("ingestion", "0002_rawblob_sourcefetch")]
    executor = MigrationExecutor(connection)
    executor.migrate(old_target)
    old_apps = executor.loader.project_state(old_target).apps
    old_data_source = old_apps.get_model("ingestion", "DataSource")
    old_ingestion_run = old_apps.get_model("ingestion", "IngestionRun")
    old_raw_artifact = old_apps.get_model("ingestion", "RawArtifact")
    fetched_at = timezone.now()
    source = old_data_source.objects.create(
        key="legacy-source",
        name="Legacy source",
        base_url="https://legacy.gradmatch.test/",
        enabled=True,
        rate_limit_per_minute=10,
    )
    run = old_ingestion_run.objects.create(
        source=source,
        status="succeeded",
        started_at=fetched_at,
        finished_at=fetched_at,
    )
    old_raw_artifact.objects.create(
        source=source,
        run=run,
        content_hash="b" * 64,
        storage_key="ingestion/raw/bb/legacy.html",
        source_url="https://legacy.gradmatch.test/with-run.html",
        content_type="text/html",
        fetched_at=fetched_at,
    )
    old_raw_artifact.objects.create(
        source=source,
        run=None,
        content_hash="c" * 64,
        storage_key="ingestion/raw/cc/legacy-without-run.html",
        source_url="https://legacy.gradmatch.test/without-run.html",
        content_type="application/pdf",
        fetched_at=fetched_at,
    )

    executor = MigrationExecutor(connection)
    executor.migrate(new_target)
    new_apps = executor.loader.project_state(new_target).apps
    raw_blob = new_apps.get_model("ingestion", "RawBlob")
    source_fetch = new_apps.get_model("ingestion", "SourceFetch")

    assert raw_blob.objects.count() == 2
    assert source_fetch.objects.count() == 2
    migrated_fetch = source_fetch.objects.get(
        source_url="https://legacy.gradmatch.test/with-run.html"
    )
    assert migrated_fetch.source_id == source.id
    assert migrated_fetch.run_id == run.id
    assert migrated_fetch.requested_at == fetched_at
    assert migrated_fetch.fetched_at == fetched_at
    assert migrated_fetch.status == "succeeded"
    assert migrated_fetch.blob.content_hash == "b" * 64
    assert migrated_fetch.blob.storage_key == "ingestion/raw/bb/legacy.html"
    assert migrated_fetch.blob.byte_size == 0
    orphan_fetch = source_fetch.objects.get(
        source_url="https://legacy.gradmatch.test/without-run.html"
    )
    assert orphan_fetch.run.source_id == source.id
    assert orphan_fetch.run.status == "succeeded"
    assert orphan_fetch.blob.content_type == "application/pdf"
    with pytest.raises(LookupError):
        new_apps.get_model("ingestion", "RawArtifact")


def _fail_network_connection(*args: object, **kwargs: object) -> socket.socket:
    del args, kwargs
    raise AssertionError("The smoke fixture adapter must not open a network connection.")


class FailingAdapter:
    key = "failing-fixture"

    def fetch(self, context: FetchContext) -> FetchResult:
        return FetchResult(
            body=b"<html><body><article data-record-id='failing'></article></body></html>",
            source_url=context.base_url,
            content_type="text/html",
            fetched_at=timezone.now(),
        )

    def parse(self, result: FetchResult) -> Iterable[ParsedItem]:
        del result
        raise RuntimeError("token=very-secret\nA parser failure occurred")


class FetchFailingAdapter:
    key = "fetch-failing-fixture"

    def fetch(self, context: FetchContext) -> FetchResult:
        del context
        raise RuntimeError("token=very-secret\nA fetch failure occurred")

    def parse(self, result: FetchResult) -> Iterable[ParsedItem]:
        del result
        raise AssertionError("parse must not run after a failed access")


class MetadataAdapter:
    key = "metadata-fixture"

    def fetch(self, context: FetchContext) -> FetchResult:
        del context
        return FetchResult(
            body=b"<html><body>metadata</body></html>",
            source_url="https://fixtures.gradmatch.test/redirected.html",
            content_type="text/html",
            fetched_at=timezone.now(),
            http_status=200,
            etag='"fixture-v1"',
            last_modified="Wed, 02 Sep 2026 08:00:00 GMT",
        )

    def parse(self, result: FetchResult) -> Iterable[ParsedItem]:
        del result
        return ()


class FailingArtifactStore:
    def put(self, storage_key: str, body: bytes, content_type: str) -> None:
        del storage_key, body, content_type
        raise RuntimeError("Object storage unavailable")
