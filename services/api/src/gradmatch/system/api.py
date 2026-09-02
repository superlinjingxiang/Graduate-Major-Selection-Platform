from __future__ import annotations

from typing import Literal, Protocol, cast

import boto3
from botocore.config import Config
from django.conf import settings
from django.db import DatabaseError, connections
from django.http import HttpRequest
from ninja import NinjaAPI, Schema, Status
from ninja.security import django_auth
from redis import Redis

from gradmatch.accounts.authentication import x_session_token_header_auth
from gradmatch.accounts.models import User
from gradmatch.catalog.api import router as catalog_router


class RedisProbe(Protocol):
    def ping(self) -> bool: ...


class LiveStatusResponse(Schema):
    status: Literal["ok"]


HealthStatus = Literal["ok", "error"]


class ReadinessResponse(Schema):
    status: HealthStatus
    checks: dict[str, HealthStatus]


class MetaResponse(Schema):
    name: str
    environment: str
    version: str


class CurrentUserResponse(Schema):
    id: int
    email: str


api = NinjaAPI(
    title="GradMatch API",
    version="1.0.0",
    urls_namespace="gradmatch_api_v1",
    openapi_url="/openapi.json",
)
api.add_router("", catalog_router)


@api.get("/health/live", response=LiveStatusResponse, operation_id="get_liveness")
def live_health(request: HttpRequest) -> LiveStatusResponse:
    del request
    return LiveStatusResponse(status="ok")


@api.get(
    "/health/ready",
    response={200: ReadinessResponse, 503: ReadinessResponse},
    operation_id="get_readiness",
)
def ready_health(request: HttpRequest) -> Status[ReadinessResponse]:
    del request
    checks = check_readiness()
    status: HealthStatus = "ok" if all(value == "ok" for value in checks.values()) else "error"
    http_status = 200 if status == "ok" else 503
    return Status(http_status, ReadinessResponse(status=status, checks=checks))


@api.get("/meta", response=MetaResponse, operation_id="get_metadata")
def meta(request: HttpRequest) -> MetaResponse:
    del request
    return MetaResponse(
        name=settings.GRADMATCH_APP_NAME,
        environment=settings.GRADMATCH_ENVIRONMENT,
        version=settings.GRADMATCH_APP_VERSION,
    )


@api.get(
    "/me",
    auth=[django_auth, x_session_token_header_auth],
    response=CurrentUserResponse,
    operation_id="get_current_user",
)
def current_user(request: HttpRequest) -> CurrentUserResponse:
    request_auth = cast(object, getattr(request, "auth", None))
    user = cast(User, request_auth)
    return CurrentUserResponse(id=user.pk, email=user.email)


def check_readiness() -> dict[str, HealthStatus]:
    return {
        "database": _check_database(),
        "redis": _check_redis(),
        "object_storage": _check_object_storage(),
    }


def _check_database() -> HealthStatus:
    try:
        connections["default"].ensure_connection()
    except DatabaseError:
        return "error"
    return "ok"


def _check_redis() -> HealthStatus:
    try:
        client = cast(
            RedisProbe,
            Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
                settings.REDIS_URL,
                socket_connect_timeout=1,
                socket_timeout=1,
            ),
        )
        client.ping()
    except Exception:
        return "error"
    return "ok"


def _check_object_storage() -> HealthStatus:
    try:
        client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            config=Config(connect_timeout=1, read_timeout=1, retries={"max_attempts": 0}),
        )
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except Exception:
        return "error"
    return "ok"
