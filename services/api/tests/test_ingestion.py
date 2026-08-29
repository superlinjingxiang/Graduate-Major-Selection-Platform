from __future__ import annotations

import hashlib
import socket
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import pytest
from django.conf import settings
from django.contrib import admin
from django.db import IntegrityError, transaction
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
from gradmatch.ingestion.models import DataSource, IngestionRun, RawArtifact
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
    assert admin.site.is_registered(RawArtifact)


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
    assert RawArtifact.objects.count() == 0


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
    artifact = RawArtifact.objects.get()
    assert run.status == IngestionRun.Status.SUCCEEDED
    assert run.records_seen == 2
    assert run.records_accepted == 2
    assert run.finished_at is not None
    assert artifact.content_hash == expected_hash
    assert artifact.source == source
    assert artifact.run == run
    assert store.objects[artifact.storage_key].body == expected_body
    assert store.objects[artifact.storage_key].content_type == "text/html"


@pytest.mark.django_db
def test_identical_raw_content_is_stored_once_across_runs() -> None:
    source = create_source()
    store = InMemoryArtifactStore()

    first_run = execute_source(source.key, artifact_store=store)
    second_run = execute_source(source.key, artifact_store=store)

    artifact = RawArtifact.objects.get()
    assert RawArtifact.objects.count() == 1
    assert len(store.objects) == 1
    assert artifact.run == first_run
    assert second_run.status == IngestionRun.Status.SUCCEEDED
    assert second_run.records_seen == 2


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
    assert RawArtifact.objects.count() == 1
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
