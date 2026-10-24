"""LabVault application configuration.

All configuration is driven by environment variables. Sensible defaults are
provided for local development; production must supply real values through
the environment. No secrets are stored in this file.
"""
import os
from dotenv import load_dotenv

# Load .env automatically when present (local development only).
load_dotenv()


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


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
    # pyodbc driver name. ODBC Driver 17 for SQL Server is the supported
    # Microsoft driver for Azure SQL Database.
    DB_DRIVER = os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    DB_SERVER = os.environ.get("DB_SERVER", "localhost")
    DB_DATABASE = os.environ.get("DB_DATABASE", "LabVault")
    DB_USERNAME = os.environ.get("DB_USERNAME")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_TRUSTED_CONNECTION = _get_bool("DB_TRUSTED_CONNECTION", False)

    # File storage
    STORAGE_PATH = os.environ.get(
        "STORAGE_PATH", os.path.join(os.getcwd(), "storage")
    )
    MAX_CONTENT_LENGTH = _get_int("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)  # 10 MB

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get(
        "SESSION_COOKIE_SAMESITE", "Lax"
    )
    # Secure cookies only when explicitly enabled (HTTPS deployments).
    SESSION_COOKIE_SECURE = _get_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = _get_int(
        "PERMANENT_SESSION_LIFETIME", 1800
    )  # 30 minutes

    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # tokens bound to session, no expiry

    # Azure Blob Storage (optional production override). When unset, local
    # protected storage is used.
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get(
        "AZURE_STORAGE_CONNECTION_STRING"
    )
    AZURE_STORAGE_CONTAINER_NAME = os.environ.get(
        "AZURE_STORAGE_CONTAINER_NAME", "labvault"
    )

    # Upload allowlist — extensions only. MIME/signature validation happens
    # in storage_service.py.
    ALLOWED_EXTENSIONS = {
        "pdf",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "ppt",
        "pptx",
        "txt",
        "csv",
        "zip",
        "py",
        "java",
        "c",
        "cpp",
        "h",
        "js",
        "html",
        "css",
        "json",
        "md",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "bmp",
    }

    # Rate limiting: failed login attempts allowed before lockout window.
    LOGIN_MAX_FAILED_ATTEMPTS = _get_int("LOGIN_MAX_FAILED_ATTEMPTS", 5)
    LOGIN_LOCKOUT_SECONDS = _get_int("LOGIN_LOCKOUT_SECONDS", 900)

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = 300
    WTF_CSRF_ENABLED = False  # tests use test client directly


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
