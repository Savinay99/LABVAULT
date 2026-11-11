"""Test settings: SQLite only. Never used for dev or production."""

import os

# Keep test settings isolated from local and production environment choices.
os.environ["DJANGO_DEBUG"] = "True"
os.environ["DJANGO_SECRET_KEY"] = "test-only-secret-key-never-use-outside-tests"

from labvault_project.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("LABVAULT_TEST_DB", str(BASE_DIR / "db_test.sqlite3")),
    }
}

# Fast password hashing for tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

ALLOWED_HOSTS = ["*"]

# Disable CSRF for simpler test client usage where not needed.
CSRF_USE_SESSIONS = False
