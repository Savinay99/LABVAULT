"""Tests for laboratory instrument inventory and interval-overlap conflict prevention."""

import datetime
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from resources.models import Instrument, InstrumentBooking, InstrumentIssue


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def student(db):
    return User.objects.create_user(
        email="student.test@univ.edu",
        username="student.test@univ.edu",
        first_name="Jane",
        last_name="Doe",
        password="ValidPassword123",
        role=User.ROLE_STUDENT,
    )


@pytest.fixture
def faculty(db):
    return User.objects.create_user(
        email="faculty.test@univ.edu",
        username="faculty.test@univ.edu",
        first_name="Dr.",
        last_name="Smith",
        password="ValidPassword123",
        role=User.ROLE_ADMIN,
    )


@pytest.fixture
def oscilloscope(db):
    return Instrument.objects.create(
        asset_id="EQ-ECE-999",
        name="Digital Storage Oscilloscope 100MHz",
        category="Electronics Bench",
        department="Electronics & Communication",
        location="Room 204",
        status=Instrument.STATUS_AVAILABLE,
        condition="Calibrated",
    )


def test_instruments_list_view(client, db, oscilloscope):
    """Instruments inventory page renders with status and department filter."""
    url = reverse("resources:instruments")
    response = client.get(url)
    assert response.status_code == 200
    assert "Digital Storage Oscilloscope 100MHz" in response.content.decode("utf-8")
    assert "EQ-ECE-999" in response.content.decode("utf-8")


def test_book_instrument_unauthenticated(client, db, oscilloscope):
    """Unauthenticated users cannot book instruments; redirected to login."""
    url = reverse("resources:book_instrument", kwargs={"pk": oscilloscope.pk})
    response = client.post(url, {
        "start_time": (timezone.now() + datetime.timedelta(days=1)).isoformat(),
        "end_time": (timezone.now() + datetime.timedelta(days=1, hours=2)).isoformat(),
        "purpose": "Filter testing",
    })
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_book_instrument_success(client, db, student, oscilloscope):
    """Authenticated user books available instrument without conflicts."""
    client.force_login(student)
    url = reverse("resources:book_instrument", kwargs={"pk": oscilloscope.pk})
    now = timezone.now()
    start = now + datetime.timedelta(days=1, hours=10)
    end = start + datetime.timedelta(hours=2)

    response = client.post(url, {
        "start_time": start.strftime("%Y-%m-%dT%H:%M"),
        "end_time": end.strftime("%Y-%m-%dT%H:%M"),
        "purpose": "Circuit wave shape observation",
    })
    assert response.status_code == 302
    booking = InstrumentBooking.objects.get(instrument=oscilloscope, user=student)
    assert booking.status == InstrumentBooking.STATUS_PENDING


def test_student_can_cancel_own_pending_booking(client, db, student, oscilloscope):
    booking = InstrumentBooking.objects.create(
        instrument=oscilloscope,
        user=student,
        start_time=timezone.now() + datetime.timedelta(days=2),
        end_time=timezone.now() + datetime.timedelta(days=2, hours=1),
        purpose="Lab practical",
        status=InstrumentBooking.STATUS_PENDING,
    )
    client.force_login(student)
    page = client.get(reverse("resources:instruments"))
    assert "Cancel request" in page.content.decode()

    response = client.post(
        reverse("resources:booking_action", args=[booking.pk]),
        {"action": "cancel"},
    )

    assert response.status_code == 302
    booking.refresh_from_db()
    assert booking.status == InstrumentBooking.STATUS_CANCELLED


def test_student_cannot_approve_booking(client, db, student, faculty, oscilloscope):
    booking = InstrumentBooking.objects.create(
        instrument=oscilloscope,
        user=student,
        start_time=timezone.now() + datetime.timedelta(days=2),
        end_time=timezone.now() + datetime.timedelta(days=2, hours=1),
        purpose="Lab practical",
        status=InstrumentBooking.STATUS_PENDING,
    )
    client.force_login(student)

    response = client.post(
        reverse("resources:booking_action", args=[booking.pk]),
        {"action": "approve"},
    )

    assert response.status_code == 403
    booking.refresh_from_db()
    assert booking.status == InstrumentBooking.STATUS_PENDING


def test_admin_can_approve_issue_and_return_instrument(
    client, db, student, faculty, oscilloscope
):
    now = timezone.now()
    booking = InstrumentBooking.objects.create(
        instrument=oscilloscope,
        user=student,
        start_time=now + datetime.timedelta(days=1),
        end_time=now + datetime.timedelta(days=1, hours=2),
        purpose="Lab practical",
        status=InstrumentBooking.STATUS_PENDING,
    )
    client.force_login(faculty)
    review_page = client.get(reverse("resources:instruments"))
    assert "Approve" in review_page.content.decode()

    response = client.post(
        reverse("resources:booking_action", args=[booking.pk]),
        {"action": "approve"},
    )
    assert response.status_code == 302
    booking.refresh_from_db()
    assert booking.status == InstrumentBooking.STATUS_APPROVED
    review_page = client.get(reverse("resources:instruments"))
    assert "Record issue" in review_page.content.decode()

    due_at = timezone.now() + datetime.timedelta(days=2)
    response = client.post(
        reverse("resources:issue_booking", args=[booking.pk]),
        {"due_at": due_at.strftime("%Y-%m-%dT%H:%M")},
    )
    assert response.status_code == 302
    booking.refresh_from_db()
    oscilloscope.refresh_from_db()
    issue = InstrumentIssue.objects.get(booking=booking)
    assert booking.status == InstrumentBooking.STATUS_ISSUED
    assert oscilloscope.status == Instrument.STATUS_IN_USE
    assert issue.issued_by == faculty

    response = client.post(
        reverse("resources:return_issue", args=[issue.pk]),
        {"return_condition": "Returned clean and calibrated."},
    )
    assert response.status_code == 302
    booking.refresh_from_db()
    oscilloscope.refresh_from_db()
    issue.refresh_from_db()
    assert booking.status == InstrumentBooking.STATUS_COMPLETED
    assert oscilloscope.status == Instrument.STATUS_AVAILABLE
    assert issue.returned_by == faculty
    assert issue.return_condition == "Returned clean and calibrated."


def test_book_instrument_interval_overlap_conflict(client, db, student, faculty, oscilloscope):
    """DSA Interval Overlap Algorithm blocks overlapping reservation attempts."""
    now = timezone.now()
    slot_start = now + datetime.timedelta(days=2, hours=10)
    slot_end = slot_start + datetime.timedelta(hours=2)

    # First booking confirmed
    InstrumentBooking.objects.create(
        instrument=oscilloscope,
        user=faculty,
        start_time=slot_start,
        end_time=slot_end,
        purpose="Faculty calibration session",
        status=InstrumentBooking.STATUS_CONFIRMED,
    )

    # Student attempts overlapping booking (starts 30 min into the slot)
    client.force_login(student)
    url = reverse("resources:book_instrument", kwargs={"pk": oscilloscope.pk})
    conflict_start = slot_start + datetime.timedelta(minutes=30)
    conflict_end = conflict_start + datetime.timedelta(hours=1)

    response = client.post(url, {
        "start_time": conflict_start.strftime("%Y-%m-%dT%H:%M"),
        "end_time": conflict_end.strftime("%Y-%m-%dT%H:%M"),
        "purpose": "Overlapping request",
    })
    assert response.status_code == 302
    # Verify second booking was rejected (only faculty booking exists)
    assert InstrumentBooking.objects.filter(instrument=oscilloscope).count() == 1


def test_book_instrument_non_overlapping_succeeds(client, db, student, faculty, oscilloscope):
    """Non-overlapping booking (after existing booking ends) succeeds."""
    now = timezone.now()
    slot_start = now + datetime.timedelta(days=3, hours=10)
    slot_end = slot_start + datetime.timedelta(hours=2)

    # Existing booking 10:00 - 12:00
    InstrumentBooking.objects.create(
        instrument=oscilloscope,
        user=faculty,
        start_time=slot_start,
        end_time=slot_end,
        purpose="Faculty calibration session",
        status=InstrumentBooking.STATUS_CONFIRMED,
    )

    # Student books 14:00 - 16:00 (no overlap)
    client.force_login(student)
    url = reverse("resources:book_instrument", kwargs={"pk": oscilloscope.pk})
    later_start = slot_end + datetime.timedelta(hours=2)
    later_end = later_start + datetime.timedelta(hours=2)

    response = client.post(url, {
        "start_time": later_start.strftime("%Y-%m-%dT%H:%M"),
        "end_time": later_end.strftime("%Y-%m-%dT%H:%M"),
        "purpose": "Afternoon practical lab",
    })
    assert response.status_code == 302
    assert InstrumentBooking.objects.filter(instrument=oscilloscope).count() == 2


def test_book_instrument_past_time_rejected(client, db, student, oscilloscope):
    """Booking with start time in the past is rejected."""
    client.force_login(student)
    url = reverse("resources:book_instrument", kwargs={"pk": oscilloscope.pk})
    past_start = timezone.now() - datetime.timedelta(hours=2)
    past_end = timezone.now() + datetime.timedelta(hours=1)

    response = client.post(url, {
        "start_time": past_start.strftime("%Y-%m-%dT%H:%M"),
        "end_time": past_end.strftime("%Y-%m-%dT%H:%M"),
        "purpose": "Past attempt",
    })
    assert response.status_code == 302
    assert not InstrumentBooking.objects.filter(instrument=oscilloscope).exists()

