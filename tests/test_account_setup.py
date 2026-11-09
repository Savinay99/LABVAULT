"""Regressions for safe account setup and registration input handling."""

import os
import subprocess
import sys

import pytest

from accounts.forms import CustomUserCreationForm
from accounts.models import User


@pytest.mark.django_db
def test_create_superuser_has_labvault_administrator_role():
    admin = User.objects.create_superuser(
        email="Admin@Example.edu",
        username="admin",
        password="StrongPass123!",
    )

    assert admin.email == "admin@example.edu"
    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert admin.is_administrator is True


@pytest.mark.django_db
def test_registration_normalizes_email_before_saving():
    form = CustomUserCreationForm(
        data={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "  ADA@Example.edu  ",
            "password1": "ValidPassword123!",
            "password2": "ValidPassword123!",
        }
    )

    assert form.is_valid(), form.errors
    user = form.save()
    assert user.email == "ada@example.edu"
    assert user.username == "ada@example.edu"


@pytest.mark.django_db
def test_registration_rejects_duplicate_email_case_insensitively():
    User.objects.create_user(
        username="ada",
        email="ada@example.edu",
        password="ValidPassword123!",
    )
    form = CustomUserCreationForm(
        data={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ADA@EXAMPLE.EDU",
            "password1": "ValidPassword123!",
            "password2": "ValidPassword123!",
        }
    )

    assert not form.is_valid()


@pytest.mark.django_db
def test_registration_requires_first_and_last_name():
    form = CustomUserCreationForm(
        data={
            "first_name": "",
            "last_name": "",
            "email": "new.person@example.edu",
            "password1": "ValidPassword123!",
            "password2": "ValidPassword123!",
        }
    )

    assert not form.is_valid()
    assert "first_name" in form.errors
    assert "last_name" in form.errors


@pytest.mark.parametrize(
    "secret", ["", "local-development-only-change-before-production"]
)
def test_production_settings_reject_missing_or_example_secret_key(secret):
    env = os.environ.copy()
    env["DJANGO_DEBUG"] = "false"
    env["DJANGO_SECRET_KEY"] = secret
    result = subprocess.run(
        [sys.executable, "-c", "import labvault_project.settings"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_launch_scripts_do_not_print_default_account_credentials():
    root = os.path.dirname(os.path.dirname(__file__))
    for filename in ("run.ps1", "run.bat"):
        contents = open(os.path.join(root, filename), encoding="utf-8").read()
        assert "Admin12345!" not in contents
        assert "Student12345!" not in contents


def test_root_run_py_uses_django_entrypoint():
    root = os.path.dirname(os.path.dirname(__file__))
    env = os.environ.copy()
    env["DJANGO_DEBUG"] = "True"
    env["DJANGO_SECRET_KEY"] = "test-only-secret-key-never-use-outside-tests"
    result = subprocess.run(
        [
            sys.executable,
            "run.py",
            "check",
            "--settings=labvault_project.settings_test",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "System check identified no issues" in result.stdout


def test_production_security_flags_default_to_secure():
    root = os.path.dirname(os.path.dirname(__file__))
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "labvault_project.settings",
            "DJANGO_DEBUG": "false",
            "DJANGO_SECRET_KEY": "valid-test-secret-not-for-production",
            "DB_ENGINE": "sqlite",
        }
    )
    for key in ("SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "DB_ENCRYPT"):
        env.pop(key, None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from django.conf import settings; print('|'.join(str(v) for v in (settings.DEBUG, settings.SESSION_COOKIE_SECURE, settings.CSRF_COOKIE_SECURE, settings.DB_ENCRYPT, settings.SECURE_SSL_REDIRECT, settings.SECURE_HSTS_SECONDS)))",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False|True|True|True|True|31536000"


def test_media_root_can_be_configured_through_environment():
    root = os.path.dirname(os.path.dirname(__file__))
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "labvault_project.settings",
            "DJANGO_DEBUG": "True",
            "DJANGO_SECRET_KEY": "test-only-secret-key-never-use-outside-tests",
            "DB_ENGINE": "sqlite",
            "MEDIA_ROOT": "local-test-media",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "from django.conf import settings; print(settings.MEDIA_ROOT)"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("local-test-media")
