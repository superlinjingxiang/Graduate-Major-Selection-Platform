from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

from gradmatch.system.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("accounts/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),
]
