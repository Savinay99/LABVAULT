"""
Django settings for LabVault project.

Environment-driven configuration. No secrets are stored in this file.
Copy `.env.example` to `.env` for local development and fill in values.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env automatically when present (local development only).
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _get_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-change-me-in-production")

DEBUG = _get_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = [
    host for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # LabVault apps
    "core",
    "accounts",
    "resources",
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

ROOT_URLCONF = "labvault_project.urls"

# Error handlers
handler403 = "labvault_project.errors.handler403"
handler404 = "labvault_project.errors.handler404"
handler413 = "labvault_project.errors.handler413"
handler500 = "labvault_project.errors.handler500"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "labvault_project.wsgi.application"


def _get_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


# Database: Azure SQL / SQL Server via django-mssql-backend when configured,
# otherwise SQLite for local development without live Azure credentials.
DB_SERVER = os.environ.get("DB_SERVER")
if DB_SERVER:
    DATABASES = {
        "default": {
            "ENGINE": "mssql",
            "NAME": os.environ.get("DB_DATABASE", "LabVault"),
            "HOST": DB_SERVER,
            "PORT": os.environ.get("DB_PORT", "1433"),
            "USER": os.environ.get("DB_USERNAME", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "OPTIONS": {
                "driver": os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server"),
                "trusted_connection": _get_bool("DB_TRUSTED_CONNECTION", False),
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = _get_bool("SESSION_COOKIE_SECURE", False)
SESSION_COOKIE_AGE = _get_int("PERMANENT_SESSION_LIFETIME", 1800)

# CSRF security
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
if _get_bool("SESSION_COOKIE_SECURE", False):
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# File upload limits
MAX_CONTENT_LENGTH = _get_int("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_CONTENT_LENGTH
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_CONTENT_LENGTH

# Azure Blob Storage (optional production override). When unset, local
# protected storage under MEDIA_ROOT is used.
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "labvault")

DEFAULT_FILE_STORAGE = "resources.storage.AzureOrLocalStorage"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}
