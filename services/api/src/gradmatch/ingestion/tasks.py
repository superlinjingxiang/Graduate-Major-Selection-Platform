from __future__ import annotations

from celery import shared_task  # pyright: ignore[reportUnknownVariableType]

from .runner import IngestionExecutionError, execute_source
from .storage import ArtifactStore, S3ArtifactStore


def get_artifact_store() -> ArtifactStore:
    return S3ArtifactStore()


@shared_task(
    name="ingestion.run_source",
    autoretry_for=(IngestionExecutionError,),
    retry_backoff=True,
    max_retries=3,
)
def run_source(source_key: str) -> int:
    run = execute_source(source_key, artifact_store=get_artifact_store())
    return run.pk
