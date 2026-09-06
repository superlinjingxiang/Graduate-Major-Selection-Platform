from __future__ import annotations

import os

from .env import build_database_config
from .settings import *  # noqa: F403
from .settings import DATABASES as BASE_DATABASES

test_database_url = os.environ.get("GRADMATCH_TEST_DATABASE_URL")
DATABASES = {  # pyright: ignore[reportConstantRedefinition]
    **BASE_DATABASES,
    "default": (
        build_database_config(test_database_url)
        if test_database_url
        else {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    ),
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"  # pyright: ignore[reportConstantRedefinition]
CELERY_TASK_ALWAYS_EAGER = True  # pyright: ignore[reportConstantRedefinition]
