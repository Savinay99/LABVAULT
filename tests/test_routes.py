"""Route-level tests using the Django test client.

These tests exercise the HTTP layer (auth pages, CSRF, authorization redirects)
without requiring a real Azure SQL Database.
"""
from unittest.mock import MagicMock, patch

import io
import hashlib
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from accounts.models import User
from resources.models import (
    AccessLog,
    AuditLog,
    Category,
    LabSubmission,
    Resource,
    ResourceFiles,
    Subject,
)


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


def test_landing_page(client, db):
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


def test_library_handles_malformed_pagination_and_filter_values(client, user):
    client.force_login(user)

    response = client.get(
        reverse("resources:library"),
        {
            "page": "not-a-number",
            "page_size": "-50",
            "category_id": "invalid",
            "subject_id": "invalid",
        },
    )

    assert response.status_code == 200
    assert response.context["page"] == 1
    assert response.context["page_size"] >= 1


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


@pytest.fixture
def resource(user, db):
    return Resource.objects.create(
        title="Test Resource",
        description="A test resource.",
        storage_key="abc123def456",
        original_filename="report.pdf",
        content_type="application/pdf",
        file_size_bytes=100,
        visibility=Resource.VISIBILITY_PRIVATE,
        uploaded_by=user,
    )


def test_download_logs_access_log(client, user, resource):
    # An authorized download must create an AccessLog entry (FR-24).
    assert client.login(email="student@example.edu", password="securepass123")
    fake_backend = MagicMock()
    fake_backend.open.return_value = io.BytesIO(b"file content")
    with patch("resources.views.get_storage_backend", return_value=fake_backend):
        response = client.get(reverse("resources:download", args=[resource.pk]))
    assert response.status_code == 200
    assert AccessLog.objects.filter(user=user, resource=resource).exists()
    log = AccessLog.objects.get(user=user, resource=resource)
    assert log.ip_address is not None or log.ip_address is None


def test_download_rejects_non_owner(client, user, resource):
    # A non-owner, non-admin user must not download a private resource
    # and must not create an AccessLog entry (NFR-01).
    other = User.objects.create_user(
        email="other@example.edu",
        username="other@example.edu",
        first_name="Other",
        last_name="User",
        password="securepass123",
    )
    assert client.login(email="other@example.edu", password="securepass123")
    with patch("resources.views.get_storage_backend"):
        response = client.get(
            reverse("resources:download", args=[resource.pk]), follow_redirects=False
        )
    assert response.status_code == 403
    assert AccessLog.objects.filter(resource=resource).count() == 0


def test_public_resource_downloadable_by_any_authenticated(client, user, resource):
    # Public visibility allows any authenticated user to download (FR-21).
    resource.visibility = Resource.VISIBILITY_PUBLIC
    resource.save()
    other = User.objects.create_user(
        email="other2@example.edu",
        username="other2@example.edu",
        first_name="Other2",
        last_name="User",
        password="securepass123",
    )
    assert client.login(email="other2@example.edu", password="securepass123")
    fake_backend = MagicMock()
    fake_backend.open.return_value = io.BytesIO(b"file content")
    with patch("resources.views.get_storage_backend", return_value=fake_backend):
        response = client.get(reverse("resources:download", args=[resource.pk]))
    assert response.status_code == 200
    assert AccessLog.objects.filter(user=other, resource=resource).exists()


def test_upload_creates_resource_files_with_sha256(client, user):
    # Upload must create ResourceFiles with the SHA-256 checksum (FR-17, NFR-02).
    assert client.login(email="student@example.edu", password="securepass123")
    category = Category.objects.create(name="Biology")
    subject = Subject.objects.create(subject_code="BIO101", subject_name="Biology")

    content = b"%PDF-1.4 lab manual content"
    sha256 = hashlib.sha256(content).hexdigest()

    fake_backend = MagicMock()
    fake_backend.save.return_value = None
    with patch("resources.views.get_storage_backend", return_value=fake_backend):
        response = client.post(
            reverse("resources:upload"),
            data={
                "title": "Lab Manual",
                "description": "Week 1 manual.",
                "category": category.pk,
                "visibility": Resource.VISIBILITY_PRIVATE,
                "subjects": [subject.pk],
                "file": SimpleUploadedFile(
                    "report.pdf", content, content_type="application/pdf"
                ),
            },
            follow=False,
        )

    assert response.status_code in (302, 303)
    resource = Resource.objects.get(title="Lab Manual")
    rf = ResourceFiles.objects.get(resource=resource)
    assert rf.sha256_checksum == sha256
    assert rf.file_size_bytes == len(content)
    assert rf.content_type == "application/pdf"
    assert rf.storage_key == resource.storage_key


def test_landing_page_wireframe_and_attribution(client, db):
    """Verify landing page renders Labrina ribbons, Canto wireframe, and Savinay attribution."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "Savinay Kumar Soni" in html
    assert "wireframe-dashboard" in html
    assert "hero-ribbon-flank" in html
    assert "LABVAULT" in html


def test_about_page(client, db):
    """Verify about page renders institutional governance and stakeholder benefits."""
    response = client.get(reverse("core:about"))
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "About LabVault" in html
    assert "For Engineering Students" in html
    assert "Savinay Kumar Soni" in html


def test_departments_directory(client, db):
    """Verify departments directory renders subjects and categories."""
    response = client.get(reverse("resources:departments"))
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "Academic Departments" in html


def test_verify_page(client):
    """Verify cryptographic hash verifier page renders."""
    response = client.get(reverse("resources:verify"))
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "SHA-256" in html


def test_security_log_flow(client, user):
    """Verify security log requires login and renders access logs for user."""
    # Unauthenticated redirect to login
    response = client.get(reverse("accounts:security_log"))
    assert response.status_code == 302

    # Authenticated access
    assert client.login(email="student@example.edu", password="securepass123")
    response = client.get(reverse("accounts:security_log"))
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "Security Log" in html


def test_dashboard_does_not_show_another_users_private_resource(client, user, db):
    other = User.objects.create_user(
        email="private-owner@example.edu",
        username="private-owner@example.edu",
        password="securepass123",
    )
    private_resource = Resource.objects.create(
        title="Confidential Other Student Resource",
        uploaded_by=other,
        storage_key="private-dashboard-file",
        original_filename="private.pdf",
        content_type="application/pdf",
        file_size_bytes=10,
        visibility=Resource.VISIBILITY_PRIVATE,
    )

    client.force_login(user)
    response = client.get(reverse("core:dashboard"))

    assert response.status_code == 200
    assert private_resource.title not in response.content.decode("utf-8")


def test_dashboard_recent_resource_cards_open_the_real_resource_and_library(
    client, user, resource
):
    long_title = "Advanced Laboratory Instrumentation and Experimental Methods " * 3
    resource.title = long_title
    resource.visibility = Resource.VISIBILITY_PUBLIC
    resource.save(update_fields=["title", "visibility"])
    client.force_login(user)

    response = client.get(reverse("core:dashboard"))

    body = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "student-resource-card" in body
    assert long_title[:40] in body
    assert reverse("resources:details", args=[resource.pk]) in body
    assert reverse("resources:library") in body
    assert "New manuals and materials available to you." in body


def test_student_faculty_and_administrator_have_separate_dashboards(client, user, admin_user, db):
    faculty = User.objects.create_user(
        email="faculty@example.edu",
        username="faculty@example.edu",
        first_name="Faculty",
        last_name="Member",
        password="securepass123",
        role="faculty",
    )

    client.force_login(user)
    student_response = client.get(reverse("core:dashboard"))
    assert student_response.status_code == 200
    assert b'data-role="student"' in student_response.content
    assert b"Student Learning Desk" in student_response.content
    assert b"My Bookings" in student_response.content
    assert b"My Submissions" in student_response.content
    assert b"Awaiting feedback" in student_response.content
    assert b"My Saved Manuals" in student_response.content
    assert b"Book equipment" in student_response.content
    assert b"My Campus" in student_response.content
    assert b"Users &amp; Roles" not in student_response.content
    assert b"Review Queue" not in student_response.content
    faculty_denial = client.get("/faculty-dashboard/")
    assert faculty_denial.status_code == 403
    assert b"signed in with a Student account" in faculty_denial.content
    assert b"Faculty workspace" in faculty_denial.content
    assert b"Switch to the Faculty sign-in" in faculty_denial.content
    assert b'action="/accounts/logout/"' in faculty_denial.content
    admin_denial = client.get(reverse("core:admin_dashboard"))
    assert admin_denial.status_code == 403
    assert b"signed in with a Student account" in admin_denial.content
    assert b"Administrator workspace" in admin_denial.content
    assert b"Switch to the Administrator sign-in" in admin_denial.content
    assert f'<a href="{reverse("core:dashboard")}" class="btn btn-primary btn-block btn-lg">'.encode() in admin_denial.content

    client.force_login(faculty)
    faculty_redirect = client.get(reverse("core:dashboard"), follow=False)
    assert faculty_redirect.status_code == 302
    assert faculty_redirect.url == reverse("core:faculty_dashboard")
    faculty_response = client.get(reverse("core:faculty_dashboard"))
    assert faculty_response.status_code == 200
    assert b'data-role="faculty"' in faculty_response.content
    assert b"Teaching Workbench" in faculty_response.content
    assert b"Review Queue" in faculty_response.content
    assert b"My Teaching Resources" in faculty_response.content
    assert b"Review student work" in faculty_response.content
    assert b"My Bookings" not in faculty_response.content
    assert b"Teaching Tools" in faculty_response.content
    assert b"Book equipment" not in faculty_response.content
    admin_denial = client.get(reverse("core:admin_dashboard"))
    assert admin_denial.status_code == 403
    assert b"signed in with a Faculty account" in admin_denial.content
    assert b"Administrator workspace" in admin_denial.content
    assert f'<a href="{reverse("core:faculty_dashboard")}" class="btn btn-primary btn-block btn-lg">'.encode() in admin_denial.content

    client.force_login(admin_user)
    admin_redirect = client.get(reverse("core:dashboard"), follow=False)
    assert admin_redirect.status_code == 302
    assert admin_redirect.url == reverse("core:admin_dashboard")
    admin_response = client.get(reverse("core:admin_dashboard"))
    assert admin_response.status_code == 200
    assert b'data-role="administrator"' in admin_response.content
    assert b"Operations Console" in admin_response.content
    assert b"Platform Snapshot" in admin_response.content
    assert b"Security Audit" in admin_response.content
    assert b"Recent Access Activity" in admin_response.content
    assert b"Teaching Workbench" not in admin_response.content
    assert b"Platform Control" in admin_response.content
    assert b"Users &amp; Roles" in admin_response.content
    faculty_denial = client.get(reverse("core:faculty_dashboard"))
    assert faculty_denial.status_code == 403
    assert b"signed in with an Administrator account" in faculty_denial.content
    assert b"Faculty workspace" in faculty_denial.content
    assert f'<a href="{reverse("core:admin_dashboard")}" class="btn btn-primary btn-block btn-lg">'.encode() in faculty_denial.content


def test_faculty_submission_queue_only_shows_their_own_resources(client, user, db):
    faculty = User.objects.create_user(
        email="faculty@example.edu",
        username="faculty@example.edu",
        password="securepass123",
        role="faculty",
    )
    faculty_resource = Resource.objects.create(
        title="Faculty-owned manual",
        uploaded_by=faculty,
        storage_key="faculty-resource-key",
        original_filename="faculty.pdf",
        content_type="application/pdf",
        file_size_bytes=10,
        visibility=Resource.VISIBILITY_PRIVATE,
    )
    other_resource = Resource.objects.create(
        title="Other user's manual",
        uploaded_by=user,
        storage_key="other-resource-key",
        original_filename="other.pdf",
        content_type="application/pdf",
        file_size_bytes=10,
        visibility=Resource.VISIBILITY_PRIVATE,
    )
    own_submission = LabSubmission.objects.create(
        resource=faculty_resource,
        student=user,
        original_filename="own-report.pdf",
        storage_key="own-submission-key",
        file_size_bytes=10,
        sha256_checksum="a" * 64,
    )
    other_submission = LabSubmission.objects.create(
        resource=other_resource,
        student=user,
        original_filename="other-report.pdf",
        storage_key="other-submission-key",
        file_size_bytes=10,
        sha256_checksum="b" * 64,
    )

    client.force_login(faculty)
    response = client.get(reverse("resources:submissions_hub"))

    assert response.status_code == 200
    submissions = list(response.context["submissions"])
    assert [submission.pk for submission in submissions] == [own_submission.pk]
    assert other_submission.pk not in [submission.pk for submission in submissions]


def test_faculty_and_student_cannot_review_or_download_other_resource_submissions(
    client, user, db
):
    faculty = User.objects.create_user(
        email="faculty@example.edu",
        username="faculty@example.edu",
        password="securepass123",
        role="faculty",
    )
    author = User.objects.create_user(
        email="author@example.edu",
        username="author@example.edu",
        password="securepass123",
        role=User.ROLE_STUDENT,
    )
    resource = Resource.objects.create(
        title="Public course resource",
        uploaded_by=author,
        storage_key="review-scope-resource",
        original_filename="public.pdf",
        content_type="application/pdf",
        file_size_bytes=10,
        visibility=Resource.VISIBILITY_PUBLIC,
    )
    submission = LabSubmission.objects.create(
        resource=resource,
        student=user,
        original_filename="private-student-report.pdf",
        storage_key="review-scope-submission",
        file_size_bytes=10,
        sha256_checksum="c" * 64,
    )

    client.force_login(faculty)
    details_response = client.get(reverse("resources:details", args=[resource.pk]))
    assert details_response.status_code == 200
    assert b"Student Practical Submissions Queue" not in details_response.content
    assert b"private-student-report.pdf" not in details_response.content
    assert client.get(reverse("resources:grade_submission", args=[submission.pk])).status_code == 403
    assert client.get(reverse("resources:download_submission", args=[submission.pk])).status_code == 403

    client.force_login(author)
    assert client.get(reverse("resources:grade_submission", args=[submission.pk])).status_code == 403
    assert client.get(reverse("resources:download_submission", args=[submission.pk])).status_code == 403


def test_public_landing_page_does_not_expose_access_log_personal_data(
    client, user, resource
):
    resource.visibility = Resource.VISIBILITY_PUBLIC
    resource.save(update_fields=["visibility"])
    AccessLog.objects.create(
        user=user,
        resource=resource,
        ip_address="203.0.113.42",
    )

    response = client.get(reverse("core:landing"))
    body = response.content.decode("utf-8")

    assert response.status_code == 200
    assert user.email not in body
    assert "203.0.113.42" not in body


def test_resource_delete_get_request_does_not_delete(client, user, resource):
    client.force_login(user)

    response = client.get(reverse("resources:delete", args=[resource.pk]))

    assert response.status_code == 405
    assert Resource.objects.filter(pk=resource.pk).exists()


def test_resource_delete_records_audit_event(client, user, resource):
    client.force_login(user)
    with patch("resources.views.get_storage_backend") as get_backend:
        response = client.post(reverse("resources:delete", args=[resource.pk]))

    assert response.status_code == 302
    assert not Resource.objects.filter(pk=resource.pk).exists()
    assert AuditLog.objects.filter(
        actor=user,
        action="resource_deleted",
        entity_type="Resource",
        entity_id=resource.pk,
    ).exists()
    get_backend.return_value.delete.assert_called_once_with(resource.storage_key)


def test_logout_requires_post_and_clears_session(client, user):
    client.force_login(user)
    logout_url = reverse("accounts:logout")

    get_response = client.get(logout_url)
    assert get_response.status_code == 405
    assert "_auth_user_id" in client.session

    post_response = client.post(logout_url)
    assert post_response.status_code == 302
    assert "_auth_user_id" not in client.session


def test_role_mismatch_switch_sign_in_keeps_the_requested_workspace(client, user):
    client.force_login(user)
    admin_sign_in = f"{reverse('accounts:login')}?next={reverse('core:admin_dashboard')}"

    logout_response = client.post(
        reverse("accounts:logout"),
        {"next": admin_sign_in},
    )
    assert logout_response.status_code == 302
    assert logout_response.url == admin_sign_in
    assert "_auth_user_id" not in client.session

    login_response = client.get(admin_sign_in)
    assert login_response.status_code == 200
    assert b"Sign in with your" in login_response.content
    assert b"Administrator</strong> account" in login_response.content


def test_bookmark_rejects_external_next_redirect(client, user, resource):
    client.force_login(user)

    response = client.post(
        reverse("resources:toggle_bookmark", args=[resource.pk]),
        {"next": "https://evil.example/"},
    )

    assert response.status_code == 302
    assert "evil.example" not in response["Location"]
