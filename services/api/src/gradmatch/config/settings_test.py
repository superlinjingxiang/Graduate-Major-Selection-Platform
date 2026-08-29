from __future__ import annotations

from .settings import *  # noqa: F403
from .settings import DATABASES as BASE_DATABASES

DATABASES = {  # pyright: ignore[reportConstantRedefinition]
    **BASE_DATABASES,
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
