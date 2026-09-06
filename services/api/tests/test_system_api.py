import pytest
from django.test import Client

from gradmatch.accounts.models import User
from gradmatch.system import api as system_api


@pytest.fixture
def staff_client(db: None) -> Client:
    del db
    user = User.objects.create_user(
        email="operations@example.test",
        password="strong-password-123",
        is_staff=True,
    )
    client = Client()
    client.force_login(user)
    return client


def test_live_health_returns_ok(client: Client) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_health_returns_ok_when_every_dependency_is_available(
    staff_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(system_api, "_check_database", lambda: "ok")
    monkeypatch.setattr(system_api, "_check_redis", lambda: "ok")
    monkeypatch.setattr(system_api, "_check_object_storage", lambda: "ok")

    response = staff_client.get("/api/v1/health/ready")

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
    staff_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(system_api, "_check_database", lambda: "error")
    monkeypatch.setattr(system_api, "_check_redis", lambda: "ok")
    monkeypatch.setattr(system_api, "_check_object_storage", lambda: "ok")

    response = staff_client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": {
            "database": "error",
            "redis": "ok",
            "object_storage": "ok",
        },
    }


def test_meta_returns_application_metadata(staff_client: Client) -> None:
    response = staff_client.get("/api/v1/meta")

    assert response.status_code == 200
    assert response.json() == {
        "name": "GradMatch API",
        "environment": "development",
        "version": "0.1.0",
    }


def test_public_requests_cannot_read_internal_diagnostics(client: Client) -> None:
    for path in ("/api/v1/health/ready", "/api/v1/meta"):
        response = client.get(path)

        assert response.status_code == 401
        serialized = response.content.decode()
        assert "database" not in serialized
        assert "development" not in serialized
        assert "0.1.0" not in serialized
