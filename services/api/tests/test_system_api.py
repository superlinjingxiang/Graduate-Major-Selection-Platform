import pytest
from django.test import Client

from gradmatch.system import api as system_api


def test_live_health_returns_ok(client: Client) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_health_returns_ok_when_every_dependency_is_available(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        system_api,
        "check_readiness",
        lambda: {
            "database": "ok",
            "redis": "ok",
            "object_storage": "ok",
        },
        raising=False,
    )

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "database": "ok",
            "redis": "ok",
            "object_storage": "ok",
        },
    }


def test_ready_health_returns_service_unavailable_when_a_dependency_fails(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        system_api,
        "check_readiness",
        lambda: {
            "database": "ok",
            "redis": "error",
            "object_storage": "ok",
        },
        raising=False,
    )

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {
            "database": "ok",
            "redis": "error",
            "object_storage": "ok",
        },
    }


def test_meta_returns_application_metadata(client: Client) -> None:
    response = client.get("/api/v1/meta")

    assert response.status_code == 200
    assert response.json() == {
        "name": "GradMatch API",
        "environment": "development",
        "version": "0.1.0",
    }
