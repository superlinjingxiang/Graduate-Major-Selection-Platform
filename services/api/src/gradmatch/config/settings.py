from __future__ import annotations

from typing import TypedDict

from django.core.exceptions import ImproperlyConfigured

from gradmatch.__about__ import __version__

from .env import build_database_config, get_bool_env, get_env, get_list_env


class TemplateOptions(TypedDict):
    context_processors: list[str]


class TemplateConfig(TypedDict):
    BACKEND: str
    DIRS: list[str]
    APP_DIRS: bool
    OPTIONS: TemplateOptions


LOCAL_ENVIRONMENTS = frozenset({"development", "test"})


GRADMATCH_APP_NAME = get_env("GRADMATCH_APP_NAME", default="GradMatch API")
GRADMATCH_ENVIRONMENT = get_env("GRADMATCH_ENVIRONMENT", default="development")
GRADMATCH_APP_VERSION = get_env("GRADMATCH_APP_VERSION", default=__version__)
IS_LOCAL_ENVIRONMENT = GRADMATCH_ENVIRONMENT in LOCAL_ENVIRONMENTS
SECRET_KEY = get_env(
    "DJANGO_SECRET_KEY",
    default="gradmatch-development-secret-key-not-for-production" if IS_LOCAL_ENVIRONMENT else "",
)
if not IS_LOCAL_ENVIRONMENT and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must contain at least 50 characters outside development and test."
    )
DEBUG = get_bool_env("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = get_list_env(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "testserver"],
)
DATABASE_URL = get_env(
    "DATABASE_URL",
    default="postgresql://gradmatch:gradmatch@localhost:5432/gradmatch",
)
REDIS_URL = get_env("REDIS_URL", default="redis://localhost:6379/0")
S3_ENDPOINT_URL = get_env("S3_ENDPOINT_URL", default="http://localhost:9000")
S3_BUCKET_NAME = get_env("S3_BUCKET_NAME", default="gradmatch")
S3_ACCESS_KEY_ID = get_env("S3_ACCESS_KEY_ID", default="gradmatch")
S3_SECRET_ACCESS_KEY = get_env("S3_SECRET_ACCESS_KEY", default="gradmatch-secret")
SECURE_COOKIES = get_bool_env("DJANGO_SECURE_COOKIES", default=not IS_LOCAL_ENVIRONMENT)
if not IS_LOCAL_ENVIRONMENT and not SECURE_COOKIES:
    raise ImproperlyConfigured(
        "DJANGO_SECURE_COOKIES must be enabled outside development and test."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "gradmatch.system",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gradmatch.config.urls"
TEMPLATES: list[TemplateConfig] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "gradmatch.config.wsgi.application"
ASGI_APPLICATION = "gradmatch.config.asgi.application"

DATABASES = {"default": build_database_config(DATABASE_URL)}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
