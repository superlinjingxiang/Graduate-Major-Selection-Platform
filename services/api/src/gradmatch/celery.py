from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gradmatch.config.settings")

app = Celery("gradmatch")
app.config_from_object(  # pyright: ignore[reportUnknownMemberType]
    "django.conf:settings", namespace="CELERY"
)
app.autodiscover_tasks()  # pyright: ignore[reportUnknownMemberType]
