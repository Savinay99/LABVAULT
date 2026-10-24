"""Route-level tests using the Django test client.

These tests exercise the HTTP layer (auth pages, CSRF, authorization redirects)
without requiring a real Azure SQL Database.
"""
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="student@example.edu",
        username="student@example.edu",
        first_name="Test",
        last_name="Student",
        password="securepass123",
        role=User.ROLE_STUDENT,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@example.edu",
        username="admin@example.edu",
        password="adminpass123",
    )


def test_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "LabVault" in body


def test_register_page(client):
    response = client.get(reverse("accounts:register"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Create an account" in body


def test_login_page(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Sign in" in body


def test_dashboard_redirects_when_anonymous(client):
    response = client.get(reverse("core:dashboard"), follow_redirects=False)
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_library_redirects_when_anonymous(client):
    response = client.get(reverse("resources:library"), follow_redirects=False)
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_upload_redirects_when_anonymous(client):
    response = client.get(reverse("resources:upload"), follow_redirects=False)
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_admin_redirects_when_anonymous(client):
    response = client.get(reverse("admin:index"), follow_redirects=False)
    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:login"))


def test_profile_routes_registered_correctly(client):
    # Profile and settings routes resolve and require login.
    response = client.get(reverse("accounts:profile"), follow_redirects=False)
    assert response.status_code == 302
    response = client.get(reverse("accounts:settings"), follow_redirects=False)
    assert response.status_code == 302


def test_404_page(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404


def test_csrf_token_present_in_forms(client):
    response = client.get(reverse("accounts:register"))
    body = response.content.decode("utf-8")
    # Django renders a CSRF hidden input named csrfmiddlewaretoken.
    assert "csrfmiddlewaretoken" in body or "csrf_token" in body.lower()


def test_login_next_redirect_rejects_external_url(client, user):
    # An external `next` URL must never be followed (open redirect).
    response = client.post(
        reverse("accounts:login") + "?next=http://evil.com/steal",
        data={"username": "student@example.edu", "password": "securepass123"},
        follow_redirects=False,
    )
    # Must not redirect to the external host.
    assert response.status_code in (302, 303)
    location = response.headers.get("Location", "")
    assert "evil.com" not in location
    assert location.endswith(reverse("core:dashboard"))


def test_login_next_redirect_allows_relative_path(client, user):
    # A same-origin relative path is still honored after login.
    response = client.post(
        reverse("accounts:login") + "?next=" + reverse("resources:library"),
        data={"username": "student@example.edu", "password": "securepass123"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert response.headers.get("Location", "").endswith(reverse("resources:library"))


def test_login_protocol_relative_next_rejected(client, user):
    # Protocol-relative URLs (//evil.com) are rejected.
    response = client.post(
        reverse("accounts:login") + "?next=//evil.com/steal",
        data={"username": "student@example.edu", "password": "securepass123"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    location = response.headers.get("Location", "")
    assert "evil.com" not in location
