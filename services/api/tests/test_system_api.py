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
    monkeypatch.setattr(system_api, "_check_database", lambda: "ok")
    monkeypatch.setattr(system_api, "_check_redis", lambda: "ok")
    monkeypatch.setattr(system_api, "_check_object_storage", lambda: "ok")

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
    monkeypatch.setattr(system_api, "_check_database", lambda: "error")
    monkeypatch.setattr(system_api, "_check_redis", lambda: "ok")
    monkeypatch.setattr(system_api, "_check_object_storage", lambda: "ok")

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {
            "database": "error",
            "redis": "ok",
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
