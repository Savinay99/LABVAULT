"""Test settings: SQLite only. Never used for dev or production."""

from labvault_project.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_test.sqlite3",
    }
}

# Fast password hashing for tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable CSRF for simpler test client usage where not needed.
CSRF_USE_SESSIONS = False
