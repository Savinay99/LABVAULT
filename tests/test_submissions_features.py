"""Comprehensive tests for LabVault submissions, bookmarks, maintenance, and audit exports.
Covers RDBMS transactions, non-repudiation audit logs, RBAC authorization, and report workflows.
"""

import io
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from resources.models import (
    AccessLog,
    Category,
    Instrument,
    InstrumentMaintenance,
    LabSubmission,
    Notification,
    Resource,
    ResourceBookmark,
    ResourceFiles,
)

User = get_user_model()


@pytest.fixture
def test_users(db):
    faculty = User.objects.create_user(
        username="prof@labvault.edu",
        email="prof@labvault.edu",
        password="FacultyPassword123!",
        first_name="Alan",
        last_name="Turing",
        role=User.ROLE_ADMIN,
    )
    student1 = User.objects.create_user(
        username="alice@labvault.edu",
        email="alice@labvault.edu",
        password="StudentPassword123!",
        first_name="Alice",
        last_name="Smith",
        role=User.ROLE_STUDENT,
    )
    student2 = User.objects.create_user(
        username="bob@labvault.edu",
        email="bob@labvault.edu",
        password="StudentPassword123!",
        first_name="Bob",
        last_name="Jones",
        role=User.ROLE_STUDENT,
    )
    admin = User.objects.create_superuser(
        username="super@labvault.edu",
        email="super@labvault.edu",
        password="AdminPassword123!",
        first_name="Root",
        last_name="Admin",
        role=User.ROLE_ADMIN,
    )
    return {
        "faculty": faculty,
        "student1": student1,
        "student2": student2,
        "admin": admin,
    }


@pytest.fixture
def sample_resource(db, test_users):
    cat = Category.objects.create(name="Computer Systems")
    res = Resource.objects.create(
        title="CS201 Operating Systems Memory Management Lab Manual",
        description="Comprehensive guide to virtual memory paging and page replacement algorithms.",
        uploaded_by=test_users["faculty"],
        category=cat,
        storage_key="manuals/cs201.pdf",
        original_filename="cs201.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        visibility=Resource.VISIBILITY_PUBLIC,
    )
    ResourceFiles.objects.create(
        resource=res,
        storage_key="manuals/cs201.pdf",
        original_filename="cs201.pdf",
        content_type="application/pdf",
        sha256_checksum="a" * 64,
        file_size_bytes=1024,
    )
    return res


@pytest.fixture
def sample_instrument(db):
    return Instrument.objects.create(
        asset_id="INST-OSC-01",
        name="Keysight 100MHz Digital Storage Oscilloscope",
        model_number="DSOX1102G",
        category="Electrical / Signals",
        department="Electrical & Computer Engineering",
        location="ECE Signal Processing Lab 304",
        status="available",
        condition="Calibrated / Good Condition",
    )


@pytest.mark.django_db
class TestBookmarkWorkflow:
    def test_toggle_bookmark_adds_and_removes(self, client, test_users, sample_resource):
        student = test_users["student1"]
        client.force_login(student)
        url = reverse("resources:toggle_bookmark", args=[sample_resource.pk])

        # 1. Add bookmark
        resp = client.post(url, follow=True)
        assert resp.status_code == 200
        assert ResourceBookmark.objects.filter(user=student, resource=sample_resource).exists()

        # 2. Toggle off bookmark
        resp = client.post(url, follow=True)
        assert resp.status_code == 200
        assert not ResourceBookmark.objects.filter(user=student, resource=sample_resource).exists()

    def test_unauthenticated_bookmark_redirects(self, client, sample_resource):
        url = reverse("resources:toggle_bookmark", args=[sample_resource.pk])
        resp = client.post(url)
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url


@pytest.mark.django_db
class TestLabSubmissionWorkflow:
    def test_student_submit_lab_report_success(self, client, test_users, sample_resource):
        student = test_users["student1"]
        client.force_login(student)

        dummy_pdf_content = b"%PDF-1.4 Mock experimental submission report content for LabVault"
        upload = SimpleUploadedFile("lab1_report.pdf", dummy_pdf_content, content_type="application/pdf")

        url = reverse("resources:submit_lab_report", args=[sample_resource.pk])
        resp = client.post(
            url,
            {
                "submission_file": upload,
                "student_notes": "Completed LRU and FIFO simulations with 10k page references.",
            },
            follow=True,
        )

        assert resp.status_code == 200
        submission = LabSubmission.objects.filter(resource=sample_resource, student=student).first()
        assert submission is not None
        assert submission.original_filename == "lab1_report.pdf"
        assert len(submission.sha256_checksum) == 64
        assert submission.file_size_bytes == len(dummy_pdf_content)
        assert submission.status == LabSubmission.STATUS_SUBMITTED

        # Verify instructor notification was generated
        assert Notification.objects.filter(recipient=test_users["faculty"]).exists()

    def test_download_submission_authorization(self, client, test_users, sample_resource):
        student1 = test_users["student1"]
        student2 = test_users["student2"]
        faculty = test_users["faculty"]

        submission = LabSubmission.objects.create(
            resource=sample_resource,
            student=student1,
            original_filename="exp_report.pdf",
            storage_key="submissions/test.pdf",
            file_size_bytes=512,
            sha256_checksum="b" * 64,
        )

        url = reverse("resources:download_submission", args=[submission.pk])

        # Student 2 is unauthorized -> 403 Forbidden
        client.force_login(student2)
        resp2 = client.get(url)
        assert resp2.status_code == 403

        # Submitting student 1 is authorized
        client.force_login(student1)
        resp1 = client.get(url)
        assert resp1.status_code in [200, 302, 404]

        # Faculty is authorized
        client.force_login(faculty)
        resp_fac = client.get(url)
        assert resp_fac.status_code in [200, 302, 404]

    def test_faculty_grade_submission_workflow(self, client, test_users, sample_resource):
        faculty = test_users["faculty"]
        student = test_users["student1"]

        submission = LabSubmission.objects.create(
            resource=sample_resource,
            student=student,
            original_filename="experiment_pager.py",
            storage_key="submissions/test_pager.py",
            file_size_bytes=256,
            sha256_checksum="c" * 64,
            status=LabSubmission.STATUS_SUBMITTED,
        )

        url = reverse("resources:grade_submission", args=[submission.pk])

        # Student cannot grade -> 403 Forbidden
        client.force_login(student)
        resp_student = client.post(url, {"grade": "95", "status": "reviewed", "faculty_feedback": "Hacked"})
        assert resp_student.status_code == 403

        # Faculty can grade
        client.force_login(faculty)
        resp_grade = client.post(
            url,
            {
                "grade": "92.0",
                "status": "reviewed",
                "faculty_feedback": "Excellent LRU cache implementation and clean page fault telemetry.",
            },
            follow=True,
        )
        assert resp_grade.status_code == 200

        submission.refresh_from_db()
        assert float(submission.grade) == 92.0
        assert submission.status == LabSubmission.STATUS_REVIEWED
        assert submission.reviewed_by == faculty
        assert "Excellent LRU cache" in submission.faculty_feedback

        # Student should receive a grade notification
        grade_notif = Notification.objects.filter(
            recipient=student
        ).first()
        assert grade_notif is not None
        assert "evaluated your submission" in grade_notif.verb


@pytest.mark.django_db
class TestInstrumentMaintenanceWorkflow:
    def test_maintenance_logging_and_condition_update(self, client, test_users, sample_instrument):
        admin = test_users["admin"]
        client.force_login(admin)

        url = reverse("resources:instrument_maintenance", args=[sample_instrument.pk])

        # GET maintenance page
        resp_get = client.get(url)
        assert resp_get.status_code == 200
        assert sample_instrument.name in resp_get.content.decode()

        # POST new calibration log
        resp_post = client.post(
            url,
            {
                "maintenance_type": "calibration",
                "description": "Recalibrated vertical deflection amplifiers to +/- 0.5% NIST tolerance.",
                "performed_date": "2026-11-08",
                "next_due_date": "2027-05-01",
                "passed_inspection": "on",
            },
            follow=True,
        )
        assert resp_post.status_code == 200

        # Verify maintenance log record created
        maint = InstrumentMaintenance.objects.filter(instrument=sample_instrument).first()
        assert maint is not None
        assert maint.maintenance_type == "calibration"
        assert "Recalibrated" in maint.description
        assert maint.technician == admin

        sample_instrument.refresh_from_db()
        assert "Calibrated" in sample_instrument.condition

    def test_student_cannot_log_maintenance(self, client, test_users, sample_instrument):
        student = test_users["student1"]
        client.force_login(student)
        url = reverse("resources:instrument_maintenance", args=[sample_instrument.pk])
        resp = client.post(
            url,
            {
                "maintenance_type": "repair",
                "description": "Unauthorized tamper test",
                "performed_date": "2026-11-08",
            },
        )
        assert resp.status_code == 403

    def test_invalid_maintenance_form_does_not_create_a_record(
        self, client, test_users, sample_instrument
    ):
        client.force_login(test_users["admin"])
        url = reverse("resources:instrument_maintenance", args=[sample_instrument.pk])

        response = client.post(
            url,
            {
                "maintenance_type": "unknown",
                "description": "Invalid date test",
                "performed_date": "not-a-date",
                "next_due_date": "also-not-a-date",
            },
        )

        assert response.status_code == 302
        assert not InstrumentMaintenance.objects.filter(instrument=sample_instrument).exists()


@pytest.mark.django_db
class TestAuditAndEquipmentExports:
    def test_export_audit_log_csv_and_json(self, client, test_users, sample_resource):
        admin = test_users["admin"]
        student = test_users["student1"]

        # Log some sample accesses
        AccessLog.objects.create(
            user=student,
            resource=sample_resource,
            ip_address="192.168.1.100",
        )

        csv_url = reverse("resources:export_audit_log") + "?format=csv"
        json_url = reverse("resources:export_audit_log") + "?format=json"

        # Student gets 403 Forbidden
        client.force_login(student)
        assert client.get(csv_url).status_code == 403

        # Admin gets 200 OK with CSV
        client.force_login(admin)
        resp_csv = client.get(csv_url)
        assert resp_csv.status_code == 200
        assert "text/csv" in resp_csv["Content-Type"]
        assert "Resource Title" in resp_csv.content.decode()
        assert "CS201 Operating Systems" in resp_csv.content.decode()

        # Admin gets 200 OK with JSON
        resp_json = client.get(json_url)
        assert resp_json.status_code == 200
        assert "application/json" in resp_json["Content-Type"]
        assert "192.168.1.100" in resp_json.content.decode()

    def test_export_equipment_report_csv(self, client, test_users, sample_instrument):
        admin = test_users["admin"]
        student = test_users["student1"]
        url = reverse("resources:export_equipment_report")

        # Student gets 403 Forbidden
        client.force_login(student)
        assert client.get(url).status_code == 403

        # Admin gets 200 OK
        client.force_login(admin)
        resp = client.get(url)
        assert resp.status_code == 200
        assert "text/csv" in resp["Content-Type"]
        assert "Keysight 100MHz" in resp.content.decode()
        assert "DSOX1102G" in resp.content.decode()


@pytest.mark.django_db
def test_notification_mark_read_is_post_only_and_rejects_external_redirect(
    client, test_users, sample_resource
):
    from django.urls import reverse

    student = test_users["student1"]
    notification = Notification.objects.create(
        recipient=student,
        verb="Test notification",
        target_url="https://evil.example/",
    )
    client.force_login(student)
    url = reverse("resources:notification_mark_read", args=[notification.pk])

    get_response = client.get(url)
    notification.refresh_from_db()
    assert get_response.status_code == 405
    assert notification.is_read is False

    post_response = client.post(url)
    assert post_response.status_code == 302
    assert "evil.example" not in post_response["Location"]
    assert post_response["Location"].endswith(
        reverse("resources:notifications")
    )
    notification.refresh_from_db()
    assert notification.is_read is True


@pytest.mark.django_db
def test_grade_submission_rejects_unknown_status(client, test_users, sample_resource):
    faculty = test_users["faculty"]
    student = test_users["student1"]
    submission = LabSubmission.objects.create(
        resource=sample_resource,
        student=student,
        original_filename="experiment.py",
        storage_key="submissions/grade-validation.py",
        file_size_bytes=100,
        sha256_checksum="d" * 64,
    )
    client.force_login(faculty)

    response = client.post(
        reverse("resources:grade_submission", args=[submission.pk]),
        {"grade": "90", "status": "forged", "faculty_feedback": "test"},
    )

    assert response.status_code == 302
    submission.refresh_from_db()
    assert submission.status == LabSubmission.STATUS_SUBMITTED
    assert submission.grade is None
