"""
Django settings for LabVault project.

Environment-driven configuration. No secrets are stored in this file.
Copy `.env.example` to `.env` for local development and fill in values.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
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


DEBUG = _get_bool("DJANGO_DEBUG", False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip()
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false."
        )
    SECRET_KEY = get_random_secret_key()
elif not DEBUG and SECRET_KEY.startswith(
    ("change-this-to-", "local-development-only")
):
    raise ImproperlyConfigured(
        "Replace the example DJANGO_SECRET_KEY with a generated secret before production."
    )

ALLOWED_HOSTS = [
    host for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if host
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Social auth (Google, Microsoft, GitHub)
    "social_django",
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
    # Social auth exception middleware
    "social_django.middleware.SocialAuthExceptionMiddleware",
]
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

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
                "resources.context_processors.unread_notification_count",
            ],
        },
    },
]

WSGI_APPLICATION = "labvault_project.wsgi.application"


# Database: SQL Server is the default for development and production.
# Read all connection details from .env. SQLite is used only in
# settings_test.py (tests) and never in dev or prod.
DB_ENGINE = os.environ.get("DB_ENGINE", "mssql")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "1433")
DB_NAME = os.environ.get("DB_NAME", "LabVault")
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_DRIVER = os.environ.get("DB_DRIVER", "ODBC Driver 18 for SQL Server")
DB_TRUSTED_CONNECTION = _get_bool("DB_TRUSTED_CONNECTION", False)
DB_ENCRYPT = _get_bool("DB_ENCRYPT", True)
DB_AUTH_MODE = os.environ.get("DB_AUTH_MODE", "password").strip().lower()

if DB_ENGINE == "mssql":
    DATABASES = {
        "default": {
            "ENGINE": "mssql",
            "NAME": DB_NAME,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "OPTIONS": {
                "driver": DB_DRIVER,
                "trusted_connection": DB_TRUSTED_CONNECTION,
            },
        }
    }

    sql_extra_params = []
    if DB_ENCRYPT:
        sql_extra_params.extend(["Encrypt=yes", "TrustServerCertificate=no"])
    if DB_AUTH_MODE == "managed_identity":
        sql_extra_params.append("Authentication=ActiveDirectoryMsi")
        DATABASES["default"].pop("USER")
        DATABASES["default"].pop("PASSWORD")
    elif DB_AUTH_MODE != "password":
        raise ImproperlyConfigured("DB_AUTH_MODE must be 'password' or 'managed_identity'.")
    if sql_extra_params:
        DATABASES["default"]["OPTIONS"]["extra_params"] = ";".join(sql_extra_params)
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password hashing: Argon2 is the required hasher (FR-04, NFR-03).
# `argon2-cffi` must be installed for this to take effect at runtime.
# See requirements.txt; install with `pip install argon2-cffi`.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

AUTHENTICATION_BACKENDS = [
    # Social auth backends
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.microsoft.MicrosoftOAuth2",
    "social_core.backends.github.GithubOAuth2",
    # Default Django backend
    "django.contrib.auth.backends.ModelBackend",
]

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
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}
if not DEBUG:
    STORAGES["staticfiles"]["BACKEND"] = (
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )

# App Service terminates HTTPS at its front-end proxy and forwards this trusted
# header to the Django worker, allowing secure redirects to detect HTTPS.
if os.environ.get("WEBSITE_SITE_NAME"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MEDIA_URL = "/media/"
_media_root = Path(os.environ.get("MEDIA_ROOT", "media")).expanduser()
MEDIA_ROOT = _media_root if _media_root.is_absolute() else BASE_DIR / _media_root

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = _get_bool("SESSION_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_AGE = _get_int("PERMANENT_SESSION_LIFETIME", 1800)

# CSRF security
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = _get_bool("CSRF_COOKIE_SECURE", not DEBUG)
if not DEBUG and not (SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE):
    raise ImproperlyConfigured(
        "Secure session and CSRF cookies must be enabled when DJANGO_DEBUG is false."
    )
CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]

# ---------- Social Auth (Google, Microsoft, GitHub) ----------
SOCIAL_AUTH_URL_NAMESPACE = "social"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "core:dashboard"
SOCIAL_AUTH_LOGIN_ERROR_URL = "accounts:login"
SOCIAL_AUTH_LOGIN_URL = "accounts:login"
SOCIAL_AUTH_SLUGIFY_USERNAMES = True
SOCIAL_AUTH_CLEAN_USERNAMES = True
SOCIAL_AUTH_CHANGE_SIGNAL_ONLY = False

# OAuth credentials — configure via .env (social auth will not work without real keys)
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["openid", "email", "profile"]

SOCIAL_AUTH_MICROSOFT_OAUTH2_KEY = os.environ.get("SOCIAL_AUTH_MICROSOFT_OAUTH2_KEY", "")
SOCIAL_AUTH_MICROSOFT_OAUTH2_SECRET = os.environ.get("SOCIAL_AUTH_MICROSOFT_OAUTH2_SECRET", "")
SOCIAL_AUTH_MICROSOFT_OAUTH2_SCOPE = ["openid", "email", "profile"]

SOCIAL_AUTH_GITHUB_KEY = os.environ.get("SOCIAL_AUTH_GITHUB_KEY", "")
SOCIAL_AUTH_GITHUB_SECRET = os.environ.get("SOCIAL_AUTH_GITHUB_SECRET", "")
SOCIAL_AUTH_GITHUB_SCOPE = ["user:email", "read:user"]

# Social auth pipeline — auto-create users on first social login
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "accounts.social_pipeline.create_user_by_email",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_SSL_REDIRECT = _get_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = _get_int(
    "SECURE_HSTS_SECONDS", 31536000 if not DEBUG else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _get_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG
)

# File upload limits
MAX_CONTENT_LENGTH = _get_int("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_CONTENT_LENGTH
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_CONTENT_LENGTH

# Email configuration (Safe console default for development; SMTP for production)
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = _get_int("EMAIL_PORT", 587)
EMAIL_USE_TLS = _get_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "LabVault <no-reply@labvault.local>")
PASSWORD_RESET_TIMEOUT = 1800  # 30 minutes expiration
LOGIN_MAX_FAILED_ATTEMPTS = max(1, _get_int("LOGIN_MAX_FAILED_ATTEMPTS", 5))
LOGIN_LOCKOUT_SECONDS = max(1, _get_int("LOGIN_LOCKOUT_SECONDS", 900))

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
