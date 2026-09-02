from __future__ import annotations

from pathlib import Path
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
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "allauth.socialaccount",
    "gradmatch.accounts",
    "gradmatch.advising",
    "gradmatch.catalog",
    "gradmatch.ingestion",
    "gradmatch.system",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
SITE_ID = 1

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_SUPPORTS_RESEND = True
ACCOUNT_LOGIN_BY_CODE_FORMAT = {
    "numeric": True,
    "length": 6,
    "dashed": False,
}
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_PREVENT_ENUMERATION = True

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    }
]

HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser", "app")
HEADLESS_SERVE_SPECIFICATION = True
HEADLESS_TOKEN_STRATEGY = "allauth.headless.tokens.strategies.sessions.SessionTokenStrategy"
WEB_BASE_URL = get_env("WEB_BASE_URL", default="http://localhost:3000").rstrip("/")
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{WEB_BASE_URL}/account/verify-email/{{key}}",
    "account_reset_password_from_key": f"{WEB_BASE_URL}/account/password/reset/{{key}}",
    "account_signup": f"{WEB_BASE_URL}/account/signup",
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_FROM_EMAIL = get_env("EMAIL_FROM", default="noreply@example.test")
EMAIL_HOST = get_env("EMAIL_SMTP_HOST", default="localhost")
EMAIL_PORT = int(get_env("EMAIL_SMTP_PORT", default="1025"))
EMAIL_HOST_USER = get_env("EMAIL_SMTP_USER", default="")
EMAIL_HOST_PASSWORD = get_env("EMAIL_SMTP_PASSWORD", default="")
EMAIL_USE_TLS = get_bool_env("EMAIL_USE_TLS", default=False)

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = get_bool_env("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = get_bool_env("CELERY_TASK_EAGER_PROPAGATES", default=True)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

BASE_DIR = Path(__file__).resolve().parents[3]
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
