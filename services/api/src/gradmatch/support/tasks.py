from __future__ import annotations

from celery import shared_task  # pyright: ignore[reportUnknownVariableType]
from django.utils import timezone

from .services import dispatch_pending_outbox_events, process_recomputation_event


@shared_task(name="support.dispatch_outbox_events")
def dispatch_outbox_events() -> int:
    return dispatch_pending_outbox_events(now=timezone.now())


@shared_task(name="support.recompute_published_correction")
def recompute_published_correction(event_key: str) -> dict[str, int]:
    return process_recomputation_event(event_key=event_key)
