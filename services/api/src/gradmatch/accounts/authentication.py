from __future__ import annotations

from typing import cast

from allauth.headless.contrib.ninja.security import x_session_token_auth
from django.http import HttpRequest
from ninja.security import APIKeyHeader

from .models import User


class XSessionTokenHeaderAuth(APIKeyHeader):
    param_name = "X-Session-Token"

    def authenticate(self, request: HttpRequest, key: str | None) -> User | None:
        if not key:
            return None
        return cast(User | None, x_session_token_auth(request))


x_session_token_header_auth = XSessionTokenHeaderAuth()
