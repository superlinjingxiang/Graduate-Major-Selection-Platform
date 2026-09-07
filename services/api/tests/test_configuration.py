from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from gradmatch.config.env import build_database_config

API_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = API_ROOT.parent.parent


def import_settings_in_subprocess(
    *,
    expression: str = "settings.SESSION_COOKIE_SECURE",
    **environment: str,
) -> subprocess.CompletedProcess[str]:
    child_environment = os.environ.copy()
    for variable_name in (
        "DJANGO_SECRET_KEY",
        "DJANGO_SECURE_COOKIES",
        "GRADMATCH_ENVIRONMENT",
    ):
        child_environment.pop(variable_name, None)
    child_environment.update(environment)
    child_environment["PYTHONPATH"] = str(API_ROOT / "src")

    return subprocess.run(
        [
            sys.executable,
            "-c",
            f"from gradmatch.config import settings; print({expression})",
        ],
        capture_output=True,
        check=False,
        cwd=API_ROOT,
        env=child_environment,
        text=True,
    )


def test_env_example_uses_the_django_runtime_configuration_names() -> None:
    environment_example = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "GRADMATCH_APP_NAME=GradMatch" in environment_example
    assert "S3_ENDPOINT_URL=http://localhost:9000" in environment_example
    assert "DJANGO_SETTINGS_MODULE=gradmatch.config.settings" in environment_example


def test_postgresql_configuration_limits_connection_time() -> None:
    database_config = build_database_config("postgresql://user:password@database:5432/gradmatch")

    assert database_config["OPTIONS"] == {"connect_timeout": "1"}


def test_settings_load_csrf_trusted_origins_for_native_web_development() -> None:
    result = import_settings_in_subprocess(
        expression="','.join(settings.CSRF_TRUSTED_ORIGINS)",
        DJANGO_CSRF_TRUSTED_ORIGINS=(
            "http://localhost:3000,http://127.0.0.1:3000"
        ),
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "http://localhost:3000,http://127.0.0.1:3000"


def test_production_settings_require_an_explicit_secret_key() -> None:
    result = import_settings_in_subprocess(GRADMATCH_ENVIRONMENT="production")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_production_settings_enable_secure_cookies_by_default() -> None:
    result = import_settings_in_subprocess(
        DJANGO_SECRET_KEY="a" * 50,
        GRADMATCH_ENVIRONMENT="production",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "True"


def test_production_settings_reject_insecure_cookies() -> None:
    result = import_settings_in_subprocess(
        DJANGO_SECRET_KEY="a" * 50,
        DJANGO_SECURE_COOKIES="false",
        GRADMATCH_ENVIRONMENT="production",
    )

    assert result.returncode != 0
    assert "DJANGO_SECURE_COOKIES" in result.stderr
