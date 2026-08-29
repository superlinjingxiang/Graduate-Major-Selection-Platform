from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gradmatch.config.settings")

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_DIRECTORY = WORKSPACE_ROOT / "packages" / "api-client" / "openapi"


def write_schema(filename: str, schema: dict[str, Any]) -> None:
    OPENAPI_DIRECTORY.mkdir(parents=True, exist_ok=True)
    (OPENAPI_DIRECTORY / filename).write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    django.setup()

    from django.test import Client

    from gradmatch.system.api import api

    core_schema = cast(dict[str, Any], api.get_openapi_schema(path_prefix="/api/v1"))
    headless_response = Client().get("/_allauth/openapi.json")
    if headless_response.status_code != 200:
        raise RuntimeError(
            f"allauth Headless OpenAPI export failed with HTTP {headless_response.status_code}."
        )

    auth_schema = cast(dict[str, Any], headless_response.json())
    write_schema("core.openapi.json", core_schema)
    write_schema("auth.openapi.json", auth_schema)


if __name__ == "__main__":
    main()
