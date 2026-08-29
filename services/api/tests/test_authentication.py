from __future__ import annotations

import json
import re
from typing import cast
from urllib.parse import unquote

import pytest
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client
from django.test.utils import override_settings

from gradmatch.accounts.models import User
from gradmatch.system.api import api


def create_verified_user(email: str = "verified@example.test") -> User:
    user = User.objects.create_user(email=email, password="strong-password-123")
    EmailAddress.objects.create(email=user.email, primary=True, user=user, verified=True)
    return user


def email_body() -> str:
    return str(mail.outbox[-1].body)


def test_authentication_uses_a_custom_email_identity_user() -> None:
    user_model = cast(type[User], get_user_model())

    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert user_model.USERNAME_FIELD == "email"
    assert user_model.REQUIRED_FIELDS == []


def test_custom_user_is_available_in_django_admin() -> None:
    assert admin.site.is_registered(User)


def test_headless_authentication_requires_verified_email_and_supports_both_login_methods() -> None:
    assert getattr(settings, "ACCOUNT_EMAIL_VERIFICATION", None) == "mandatory"
    assert getattr(settings, "ACCOUNT_LOGIN_METHODS", None) == {"email"}
    assert getattr(settings, "ACCOUNT_LOGIN_BY_CODE_ENABLED", None) is True
    assert getattr(settings, "ACCOUNT_LOGIN_BY_CODE_SUPPORTS_RESEND", None) is True
    assert getattr(settings, "ACCOUNT_PREVENT_ENUMERATION", None) is True


def test_headless_supports_browser_and_app_sessions_without_jwt() -> None:
    assert getattr(settings, "HEADLESS_ONLY", None) is True
    assert set(getattr(settings, "HEADLESS_CLIENTS", ())) == {"app", "browser"}
    assert "sessions.SessionTokenStrategy" in getattr(settings, "HEADLESS_TOKEN_STRATEGY", "")
    assert not any(name.startswith("HEADLESS_JWT") for name in dir(settings))


def test_headless_openapi_specification_is_served(client: Client) -> None:
    response = client.get("/_allauth/openapi.json")

    assert response.status_code == 200
    specification = response.json()
    assert "openapi" in specification
    assert "/_allauth/{client}/v1/auth/login" in specification["paths"]
    assert "/_allauth/{client}/v1/auth/code/confirm" in specification["paths"]


def test_core_openapi_specification_exposes_the_authenticated_user_contract() -> None:
    specification = api.get_openapi_schema(path_prefix="/api/v1")

    assert "/api/v1/me" in specification["paths"]
    assert specification["components"]["securitySchemes"]["XSessionTokenHeaderAuth"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-Session-Token",
    }


def test_current_user_endpoint_rejects_anonymous_requests(client: Client) -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 401


@pytest.mark.django_db
def test_unverified_signup_cannot_access_the_current_user_endpoint(client: Client) -> None:
    response = client.post(
        "/_allauth/browser/v1/auth/signup",
        data=json.dumps({"email": "pending@example.test", "password": "strong-password-123"}),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert client.get("/api/v1/me").status_code == 401


@pytest.mark.django_db
def test_email_verification_allows_a_new_user_to_log_in_with_a_password() -> None:
    signup_client = Client()
    signup_response = signup_client.post(
        "/_allauth/browser/v1/auth/signup",
        data=json.dumps({"email": "new@example.test", "password": "strong-password-123"}),
        content_type="application/json",
    )
    assert signup_response.status_code == 401

    key_match = re.search(r"/account/verify-email/([^\s]+)", email_body())
    assert key_match is not None

    verification_response = signup_client.post(
        "/_allauth/browser/v1/auth/email/verify",
        data=json.dumps({"key": unquote(key_match.group(1))}),
        content_type="application/json",
    )
    assert verification_response.status_code == 401

    login_client = Client()
    login_response = login_client.post(
        "/_allauth/browser/v1/auth/login",
        data=json.dumps({"email": "new@example.test", "password": "strong-password-123"}),
        content_type="application/json",
    )
    assert login_response.status_code == 200
    assert login_client.get("/api/v1/me").status_code == 200


@pytest.mark.django_db
def test_verified_user_can_log_in_with_password_and_use_browser_session(client: Client) -> None:
    user = create_verified_user()

    response = client.post(
        "/_allauth/browser/v1/auth/login",
        data=json.dumps({"email": user.email, "password": "strong-password-123"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert client.get("/api/v1/me").json() == {"id": user.pk, "email": user.email}


@pytest.mark.django_db
def test_verified_user_can_log_in_with_a_one_time_code(client: Client) -> None:
    user = create_verified_user("code@example.test")

    request_response = client.post(
        "/_allauth/browser/v1/auth/code/request",
        data=json.dumps({"email": user.email}),
        content_type="application/json",
    )
    assert request_response.status_code == 401

    match = re.search(
        r"\b([BCDFGHJKLMNPQRSTVWXZ]{4}-[BCDFGHJKLMNPQRSTVWXZ]{4})\b",
        email_body(),
    )
    assert match is not None

    confirm_response = client.post(
        "/_allauth/browser/v1/auth/code/confirm",
        data=json.dumps({"code": match.group(1)}),
        content_type="application/json",
    )

    assert confirm_response.status_code == 200
    assert client.get("/api/v1/me").json() == {"id": user.pk, "email": user.email}


@pytest.mark.django_db
def test_one_time_code_locks_after_three_incorrect_attempts(client: Client) -> None:
    user = create_verified_user("attempts@example.test")
    request_response = client.post(
        "/_allauth/browser/v1/auth/code/request",
        data=json.dumps({"email": user.email}),
        content_type="application/json",
    )
    assert request_response.status_code == 401

    for _ in range(3):
        invalid_response = client.post(
            "/_allauth/browser/v1/auth/code/confirm",
            data=json.dumps({"code": "WRONG-CODE"}),
            content_type="application/json",
        )
        assert invalid_response.status_code == 400

    assert (
        client.post(
            "/_allauth/browser/v1/auth/code/confirm",
            data=json.dumps({"code": "WRONG-CODE"}),
            content_type="application/json",
        ).status_code
        == 409
    )


@pytest.mark.django_db
def test_one_time_code_resend_has_a_limited_quota(client: Client) -> None:
    user = create_verified_user("resend@example.test")
    request_response = client.post(
        "/_allauth/browser/v1/auth/code/request",
        data=json.dumps({"email": user.email}),
        content_type="application/json",
    )
    assert request_response.status_code == 401

    for _ in range(2):
        assert client.post("/_allauth/browser/v1/auth/code/resend").status_code == 200

    assert client.post("/_allauth/browser/v1/auth/code/resend").status_code == 409


@pytest.mark.django_db
@override_settings(ACCOUNT_LOGIN_BY_CODE_TIMEOUT=0)
def test_one_time_code_expires_before_confirmation(client: Client) -> None:
    user = create_verified_user("expiry@example.test")
    request_response = client.post(
        "/_allauth/browser/v1/auth/code/request",
        data=json.dumps({"email": user.email}),
        content_type="application/json",
    )
    assert request_response.status_code == 401

    code_match = re.search(
        r"\b([BCDFGHJKLMNPQRSTVWXZ]{4}-[BCDFGHJKLMNPQRSTVWXZ]{4})\b",
        email_body(),
    )
    assert code_match is not None

    expired_response = client.post(
        "/_allauth/browser/v1/auth/code/confirm",
        data=json.dumps({"code": code_match.group(1)}),
        content_type="application/json",
    )
    assert expired_response.status_code == 409


@pytest.mark.django_db
def test_login_code_request_does_not_reveal_whether_an_email_exists(client: Client) -> None:
    known_user = create_verified_user("known@example.test")

    known_response = client.post(
        "/_allauth/browser/v1/auth/code/request",
        data=json.dumps({"email": known_user.email}),
        content_type="application/json",
    )
    anonymous_response = Client().post(
        "/_allauth/browser/v1/auth/code/request",
        data=json.dumps({"email": "unknown@example.test"}),
        content_type="application/json",
    )

    assert known_response.status_code == anonymous_response.status_code == 401


@pytest.mark.django_db
def test_current_user_endpoint_accepts_an_app_session_token() -> None:
    user = create_verified_user()
    app_client = Client()
    login_response = app_client.post(
        "/_allauth/app/v1/auth/login",
        data=json.dumps({"email": user.email, "password": "strong-password-123"}),
        content_type="application/json",
    )
    assert login_response.status_code == 200

    login_body = cast(dict[str, object], login_response.json())
    login_meta = cast(dict[str, object], login_body["meta"])
    session_token = cast(str, login_meta["session_token"])

    response = Client().get("/api/v1/me", HTTP_X_SESSION_TOKEN=session_token)

    assert response.status_code == 200
    assert response.json() == {"id": user.pk, "email": user.email}
