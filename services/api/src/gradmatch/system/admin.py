from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest


class ReadOnlyHistoryAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    """Expose workflow records for inspection without mutation shortcuts."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        del request, obj
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        del request, obj
        return False
