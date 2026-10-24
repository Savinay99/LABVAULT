"""Route-level tests using the Flask test client with a mocked database layer.

These tests exercise the HTTP layer (auth pages, CSRF, authorization redirects)
without requiring a real Azure SQL Database.
"""
import pytest
from flask import url_for


def test_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "LabVault" in body


def test_register_page(client):
    response = client.get("/auth/register")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "Create an account" in body


def test_login_page(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "Sign in" in body


def test_dashboard_redirects_when_anonymous(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 403


def test_library_redirects_when_anonymous(client):
    response = client.get("/resources/library", follow_redirects=False)
    assert response.status_code == 403


def test_upload_redirects_when_anonymous(client):
    response = client.get("/resources/upload", follow_redirects=False)
    assert response.status_code == 403


def test_admin_redirects_when_anonymous(client):
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code == 403


def test_profile_routes_registered_correctly(client):
    # Regression: blueprint URL prefixes must not repeat in route paths.
    response = client.get("/profile/", follow_redirects=False)
    assert response.status_code == 403  # requires login, but path resolves
    response = client.get("/profile/settings", follow_redirects=False)
    assert response.status_code == 403


def test_admin_routes_registered_correctly(client):
    response = client.get("/admin/users", follow_redirects=False)
    assert response.status_code == 403
    response = client.get("/admin/resources", follow_redirects=False)
    assert response.status_code == 403
    response = client.get("/admin/audit", follow_redirects=False)
    assert response.status_code == 403


def test_404_page(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404


def test_csrf_token_present_in_forms(client):
    response = client.get("/auth/register")
    body = response.data.decode("utf-8")
    # Flask-WTF injects a CSRF token input into rendered forms.
    assert "csrf_token" in body or "csrf" in body.lower()


def test_login_next_redirect_rejects_external_url(client, monkeypatch):
    # An external `next` URL must never be followed (open redirect).
    def fake_authenticate(email, password):
        return {
            "user_id": 1,
            "email": "student@example.edu",
            "full_name": "Test Student",
            "role": "student",
        }

    monkeypatch.setattr("app.routes.auth.auth_service.authenticate", fake_authenticate)

    response = client.post(
        "/auth/login?next=http://evil.com/steal",
        data={"email": "student@example.edu", "password": "password123"},
        follow_redirects=False,
    )
    # Must not redirect to the external host.
    assert response.status_code in (302, 303)
    location = response.headers.get("Location", "")
    assert "evil.com" not in location
    assert location.endswith(url_for("dashboard.index"))


def test_login_next_redirect_allows_relative_path(client, monkeypatch):
    # A same-origin relative path is still honored.
    def fake_authenticate(email, password):
        return {
            "user_id": 1,
            "email": "student@example.edu",
            "full_name": "Test Student",
            "role": "student",
        }

    monkeypatch.setattr("app.routes.auth.auth_service.authenticate", fake_authenticate)

    response = client.post(
        "/auth/login?next=/resources/library",
        data={"email": "student@example.edu", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert response.headers.get("Location", "").endswith("/resources/library")


def test_login_protocol_relative_next_rejected(client, monkeypatch):
    # Protocol-relative URLs (//evil.com) are rejected.
    def fake_authenticate(email, password):
        return {
            "user_id": 1,
            "email": "student@example.edu",
            "full_name": "Test Student",
            "role": "student",
        }

    monkeypatch.setattr("app.routes.auth.auth_service.authenticate", fake_authenticate)

    response = client.post(
        "/auth/login?next=//evil.com/steal",
        data={"email": "student@example.edu", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert "evil.com" not in response.headers.get("Location", "")
