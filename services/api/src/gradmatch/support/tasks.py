from __future__ import annotations

from celery import shared_task  # pyright: ignore[reportUnknownVariableType]

from .services import process_recomputation_event


@shared_task(name="support.recompute_published_correction")
def recompute_published_correction(event_key: str) -> dict[str, int]:
    return process_recomputation_event(event_key=event_key)
