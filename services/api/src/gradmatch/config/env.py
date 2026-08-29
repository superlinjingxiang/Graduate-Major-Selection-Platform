from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parents[3]

TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})
FALSY_VALUES = frozenset({"0", "false", "no", "off"})


def get_env(name: str, *, default: str) -> str:
    return os.environ.get(name, default)


def get_bool_env(name: str, *, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()
    if normalized_value in TRUTHY_VALUES:
        return True
    if normalized_value in FALSY_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean-like string.")


def get_list_env(name: str, *, default: list[str]) -> list[str]:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default

    return [item.strip() for item in raw_value.split(",") if item.strip()]


def build_database_config(database_url: str) -> dict[str, object]:
    parsed_url = urlparse(database_url)

    if parsed_url.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed_url.path.lstrip("/")),
            "USER": unquote(parsed_url.username or ""),
            "PASSWORD": unquote(parsed_url.password or ""),
            "HOST": parsed_url.hostname or "",
            "PORT": str(parsed_url.port or ""),
            "OPTIONS": {"connect_timeout": "1"},
        }

    if parsed_url.scheme == "sqlite":
        if parsed_url.path in {"", "/"}:
            database_name = ":memory:"
        else:
            database_name = unquote(parsed_url.path.lstrip("/"))

        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": database_name,
        }

    raise ValueError("DATABASE_URL must use the postgres/postgresql or sqlite scheme.")
