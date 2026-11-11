"""Targeted tests for authentication flow, password reset, and security."""

import pytest
from django.core import mail
from django.urls import reverse
from accounts.models import LoginAttempt, User
from django.test import override_settings
from django.utils import timezone


@pytest.mark.django_db
def test_password_reset_flow(client):
    """Verify end-to-end password reset request and email generation."""
    user = User.objects.create_user(
        username="student@univ.edu",
        email="student@univ.edu",
        password="TestSecurePassword123!",
        first_name="Alice",
        last_name="Smith",
    )

    # 1. Request password reset
    reset_url = reverse("accounts:password_reset")
    response = client.get(reset_url)
    assert response.status_code == 200
    assert "Reset Password" in response.content.decode("utf-8")

    # 2. Post email address
    post_resp = client.post(reset_url, {"email": "student@univ.edu"}, follow=True)
    assert post_resp.status_code == 200

    # Verify email was dispatched to Django test outbox
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert "LabVault Password Reset Request" in email.subject
    assert "password-reset-confirm" in email.body

    # 3. Check password reset done page
    done_resp = client.get(reverse("accounts:password_reset_done"))
    assert done_resp.status_code == 200
    assert "Check Your Email" in done_resp.content.decode("utf-8")


@pytest.mark.django_db
def test_password_reset_nonexistent_email_safe(client):
    """Verify non-existent email does not reveal account absence (prevents enumeration)."""
    mail.outbox.clear()
    reset_url = reverse("accounts:password_reset")
    response = client.post(reset_url, {"email": "nonexistent@univ.edu"}, follow=True)
    assert response.status_code == 200
    # Response must appear successful without dispatching email
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_login_validation_invalid_credentials(client):
    """Verify invalid credentials render clear error without unhandled exception."""
    login_url = reverse("accounts:login")
    response = client.post(login_url, {"username": "ghost@univ.edu", "password": "wrongpassword"})
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Invalid email or password." in content


@pytest.mark.django_db
@override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=900)
def test_django_login_locks_out_repeated_failures(client):
    login_url = reverse("accounts:login")
    payload = {"username": "locked@univ.edu", "password": "wrong"}

    for _ in range(3):
        response = client.post(login_url, payload)
        assert response.status_code == 200
        assert "Invalid email or password." in response.content.decode()

    attempt = LoginAttempt.objects.get(email="locked@univ.edu", ip_address="127.0.0.1")
    assert attempt.failed_attempts == 3
    assert attempt.locked_until > timezone.now()

    User.objects.create_user(
        username="locked@univ.edu",
        email="locked@univ.edu",
        password="CorrectPassword123!",
    )
    response = client.post(
        login_url,
        {"username": "locked@univ.edu", "password": "CorrectPassword123!"},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_successful_django_login_clears_failed_attempts(client):
    user = User.objects.create_user(
        username="returning@univ.edu",
        email="returning@univ.edu",
        password="CorrectPassword123!",
    )
    LoginAttempt.objects.create(
        email=user.email,
        ip_address="127.0.0.1",
        failed_attempts=2,
    )

    response = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "CorrectPassword123!"},
    )

    assert response.status_code == 302
    assert "_auth_user_id" in client.session
    assert not LoginAttempt.objects.filter(email=user.email).exists()


@pytest.mark.django_db
def test_login_does_not_reveal_deactivated_account_status(client):
    User.objects.create_user(
        username="inactive@univ.edu",
        email="inactive@univ.edu",
        password="CorrectPassword123!",
        is_active=False,
    )

    response = client.post(
        reverse("accounts:login"),
        {"username": "inactive@univ.edu", "password": "CorrectPassword123!"},
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "Invalid email or password." in body
    assert "deactivated" not in body.lower()

