"""Resources app views: library, upload, details, edit, delete, download."""

import csv
import json
import logging
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ResourceEditForm, ResourceUploadForm
from .models import (
    AccessLog,
    AuditLog,
    Category,
    Instrument,
    InstrumentBooking,
    InstrumentIssue,
    InstrumentMaintenance,
    LabSubmission,
    Notification,
    Resource,
    ResourceBookmark,
    ResourceFiles,
    Subject,
)
from .storage import (
    StorageError,
    compute_sha256,
    detect_mime,
    generate_storage_key,
    get_storage_backend,
    validate_file,
)

logger = logging.getLogger(__name__)


def _positive_query_int(value, default=None):
    """Parse a positive integer query parameter without raising on bad input."""
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if parsed > 0 else default


def _client_ip(request):
    """Best-effort client IP from request metadata."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _user_can_view_resource(user, resource):
    if resource.visibility == Resource.VISIBILITY_PUBLIC:
        return True
    if not user.is_authenticated:
        return False
    if user.is_administrator:
        return True
    return resource.uploaded_by_id == user.pk


def _user_can_edit_resource(user, resource):
    if not user.is_authenticated:
        return False
    if user.is_administrator:
        return True
    return resource.uploaded_by_id == user.pk


@login_required
def library(request):
    """Resource library with search, filter, sort, pagination."""
    from django.db.models import Q

    user = request.user
    page = _positive_query_int(request.GET.get("page"), 1)
    page_size = min(_positive_query_int(request.GET.get("page_size"), 20), 100)
    search = request.GET.get("search", "") or None
    category_id = _positive_query_int(request.GET.get("category_id"))
    subject_id = _positive_query_int(request.GET.get("subject_id"))
    sort = request.GET.get("sort", "created_at")
    direction = request.GET.get("direction", "DESC")

    # Whitelist sort columns/directions to prevent ordering injection.
    sort_columns = {"created_at": "created_at", "title": "title", "file_size": "file_size_bytes", "updated_at": "updated_at"}
    if direction.upper() == "ASC":
        order_by = sort_columns.get(sort, "created_at")
    else:
        order_by = "-" + sort_columns.get(sort, "created_at")

    # Base queryset: students see public + own; admins see everything.
    queryset = Resource.objects.select_related("category", "uploaded_by").prefetch_related("subjects")
    if not user.is_administrator:
        queryset = queryset.filter(
            Q(visibility=Resource.VISIBILITY_PUBLIC) | Q(uploaded_by=user)
        )
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if subject_id:
        queryset = queryset.filter(subjects__id=subject_id)

    queryset = queryset.distinct()
    total = queryset.count()
    offset = (page - 1) * page_size
    items = list(queryset.order_by(order_by)[offset:offset + page_size])

    total_pages = max(1, -(-total // page_size)) if total else 1
    categories = Category.objects.all()
    subjects = Subject.objects.all()

    context = {
        "resources": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "categories": categories,
        "subjects": subjects,
        "search": search or "",
        "category_id": int(category_id) if category_id else None,
        "subject_id": int(subject_id) if subject_id else None,
        "sort": sort,
        "direction": direction,
    }
    return render(request, "resources/library.html", context)


@login_required
def upload(request):
    """Upload a new resource."""
    if request.method == "POST":
        form = ResourceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES.get("file")
            if not uploaded_file:
                form.add_error(None, "A file is required.")
            else:
                try:
                    from .storage import get_storage_backend, validate_file, generate_storage_key
                    # Re-open the uploaded file stream for validation (Django's
                    # UploadedFile is file-like and supports seek/read).
                    file_stream = uploaded_file.file
                    ext, mime = validate_file(file_stream, uploaded_file.name)
                    storage_key = generate_storage_key(uploaded_file.name)
                    file_stream.seek(0, os.SEEK_END)
                    size_bytes = file_stream.tell()
                    file_stream.seek(0)

                    backend = get_storage_backend()
                    backend.save(file_stream, uploaded_file.name, storage_key)

                    # Compute SHA-256 over the uploaded stream before the
                    # transaction (stream is left at position 0 by compute_sha256).
                    sha256 = compute_sha256(file_stream)

                    try:
                        with transaction.atomic():
                            resource = form.save(commit=False)
                            resource.uploaded_by = request.user
                            resource.storage_key = storage_key
                            resource.original_filename = uploaded_file.name
                            resource.content_type = mime
                            resource.file_size_bytes = size_bytes
                            resource.save()
                            form.save_m2m()
                            ResourceFiles.objects.create(
                                resource=resource,
                                storage_key=storage_key,
                                original_filename=uploaded_file.name,
                                content_type=mime,
                                file_size_bytes=size_bytes,
                                sha256_checksum=sha256,
                            )
                            AuditLog.objects.create(
                                actor=request.user,
                                action="resource_uploaded",
                                entity_type="Resource",
                                entity_id=resource.pk,
                            )
                        messages.success(request, "Resource uploaded successfully.")
                        return redirect("resources:library")
                    except Exception:
                        # Roll back the file if the DB insert failed (FR-16).
                        try:
                            backend.delete(storage_key)
                        except Exception:
                            pass
                        raise
                except StorageError as exc:
                    form.add_error("file", str(exc))
                except Exception:
                    messages.error(request, "Upload failed. Please try again.")
    else:
        form = ResourceUploadForm()

    categories = Category.objects.all()
    subjects = Subject.objects.all()
    return render(request, "resources/upload.html", {
        "form": form,
        "categories": categories,
        "subjects": subjects,
    })


@login_required
def details(request, pk):
    """Resource details page with bookmarks and student submission integration."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_view_resource(request.user, resource):
        return HttpResponseForbidden("Access denied to this resource.")
    can_edit = _user_can_edit_resource(request.user, resource)

    is_bookmarked = ResourceBookmark.objects.filter(
        user=request.user, resource=resource
    ).exists()

    user_submission = None
    all_submissions = None
    can_review_submissions = request.user.is_administrator or (
        request.user.is_faculty and resource.uploaded_by_id == request.user.pk
    )
    if request.user.is_student:
        user_submission = LabSubmission.objects.filter(
            resource=resource, student=request.user
        ).first()
    elif can_review_submissions:
        all_submissions = (
            LabSubmission.objects.filter(resource=resource)
            .select_related("student")
            .order_by("-submitted_at")
        )

    return render(
        request,
        "resources/details.html",
        {
            "resource": resource,
            "can_edit": can_edit,
            "is_bookmarked": is_bookmarked,
            "user_submission": user_submission,
            "all_submissions": all_submissions,
            "can_review_submissions": can_review_submissions,
        },
    )


@login_required
def edit(request, pk):
    """Edit resource metadata."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_edit_resource(request.user, resource):
        return HttpResponseForbidden("Access denied.")

    if request.method == "POST":
        form = ResourceEditForm(request.POST, instance=resource)
        if form.is_valid():
            with transaction.atomic():
                resource = form.save()
                AuditLog.objects.create(
                    actor=request.user,
                    action="resource_updated",
                    entity_type="Resource",
                    entity_id=resource.pk,
                )
            messages.success(request, "Resource updated.")
            return redirect("resources:details", pk=resource.pk)
    else:
        form = ResourceEditForm(instance=resource)

    categories = Category.objects.all()
    subjects = Subject.objects.all()
    current_subjects = list(resource.subjects.values_list("id", flat=True))
    return render(request, "resources/edit.html", {
        "form": form,
        "resource": resource,
        "categories": categories,
        "subjects": subjects,
        "current_subjects": current_subjects,
    })


@login_required
@require_POST
def delete(request, pk):
    """Delete a resource (POST only)."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_edit_resource(request.user, resource):
        return HttpResponseForbidden("Access denied.")

    storage_key = resource.storage_key
    with transaction.atomic():
        AuditLog.objects.create(
            actor=request.user,
            action="resource_deleted",
            entity_type="Resource",
            entity_id=resource.pk,
        )
        resource.delete()  # cascade deletes related resource data
    # Best-effort file cleanup after DB delete.
    if storage_key:
        try:
            get_storage_backend().delete(storage_key)
        except Exception:
            pass
    messages.success(request, "Resource deleted.")
    return redirect("resources:library")


@login_required
def download(request, pk):
    """Download a resource file with authorization."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_view_resource(request.user, resource):
        return HttpResponseForbidden("Access denied to this resource.")

    storage_key = resource.storage_key
    backend = get_storage_backend()

    # Record the download access (FR-24, NFR-01). Best-effort: a logging
    # failure must not block an authorized download.
    ip = _client_ip(request)
    try:
        AccessLog.objects.create(user=request.user, resource=resource, ip_address=ip)
    except Exception:
        logger.warning("Failed to write AccessLog for resource %s", resource.pk)

    # Azure: issue short-lived SAS URL and redirect.
    from .storage import AzureBlobStorage
    if isinstance(backend, AzureBlobStorage):
        try:
            return redirect(backend.download_url(storage_key))
        except Exception:
            raise Http404("Unable to generate download URL.")

    # Local: stream the file with safe headers.
    file_obj = backend.open(storage_key)
    if file_obj is None:
        raise Http404("File not found.")
    response = FileResponse(
        file_obj,
        content_type=resource.content_type or "application/octet-stream",
        as_attachment=True,
        filename=resource.original_filename,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def notifications(request):
    """In-app notification center for the current user."""
    qs = request.user.notifications.all()
    unread_count = qs.filter(is_read=False).count()
    return render(
        request,
        "resources/notifications.html",
        {
            "notifications": qs,
            "unread_count": unread_count,
        },
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    """Mark a single notification as read."""
    notification = get_object_or_404(
        request.user.notifications, pk=pk
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.target_url and url_has_allowed_host_and_scheme(
        notification.target_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(notification.target_url)
    return redirect("resources:notifications")


@login_required
@require_POST
def notification_mark_all_read(request):
    """Mark all of the current user's notifications as read."""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("resources:notifications")


def departments_directory(request):
    """Academic departments and subject curriculum directory."""
    from django.db.models import Count
    subjects = Subject.objects.annotate(resource_count=Count("resources")).order_by("subject_code")
    categories = Category.objects.annotate(resource_count=Count("resource")).order_by("name")
    return render(request, "resources/departments.html", {
        "subjects": subjects,
        "categories": categories,
    })


def verify_integrity(request):
    """Interactive client-side and server-side cryptographic hash verification workstation."""
    return render(request, "resources/verify.html")


def instruments_list(request):
    """Laboratory equipment and instrument inventory."""
    dept = request.GET.get("department", "").strip()
    status = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()

    qs = Instrument.objects.filter(is_active=True)
    if dept:
        qs = qs.filter(department__icontains=dept)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            models.Q(name__icontains=q)
            | models.Q(asset_id__icontains=q)
            | models.Q(location__icontains=q)
            | models.Q(category__icontains=q)
        )

    departments = Instrument.objects.filter(is_active=True).values_list(
        "department", flat=True
    ).distinct()
    user_bookings = None
    if request.user.is_authenticated:
        bookings = InstrumentBooking.objects.select_related("instrument", "user", "issue")
        if request.user.is_administrator:
            user_bookings = bookings.exclude(
                status__in=[
                    InstrumentBooking.STATUS_CANCELLED,
                    InstrumentBooking.STATUS_REJECTED,
                    InstrumentBooking.STATUS_COMPLETED,
                ]
            ).order_by("start_time")[:25]
        else:
            user_bookings = bookings.filter(user=request.user).order_by("-start_time")[:5]

    return render(
        request,
        "resources/instruments.html",
        {
            "instruments": qs,
            "departments": departments,
            "selected_dept": dept,
            "selected_status": status,
            "query": q,
            "user_bookings": user_bookings,
            "is_admin": request.user.is_authenticated and request.user.is_administrator,
        },
    )


@login_required
def book_instrument(request, pk):
    """Reserve laboratory equipment with interval overlap conflict detection (DSA)."""
    if request.method != "POST":
        return redirect("resources:instruments")

    instrument = get_object_or_404(Instrument, pk=pk)
    if not instrument.is_active or instrument.status in (
        Instrument.STATUS_MAINTENANCE,
        Instrument.STATUS_RETIRED,
    ):
        messages.error(request, "This instrument is not currently available for booking.")
        return redirect("resources:instruments")
    start_str = request.POST.get("start_time", "").strip()
    end_str = request.POST.get("end_time", "").strip()
    purpose = request.POST.get("purpose", "").strip()

    if not start_str or not end_str or not purpose or len(purpose) > 300:
        messages.error(request, "Please provide start time, end time, and experiment purpose.")
        return redirect("resources:instruments")

    try:
        from django.utils.dateparse import parse_datetime
        start_time = parse_datetime(start_str)
        end_time = parse_datetime(end_str)
        if start_time is None or end_time is None:
            raise ValueError
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)
    except (ValueError, TypeError):
        messages.error(request, "Invalid date/time format. Please select valid reservation times.")
        return redirect("resources:instruments")

    now = timezone.now()
    if start_time < now:
        messages.error(request, "Booking start time cannot be in the past.")
        return redirect("resources:instruments")

    if end_time <= start_time:
        messages.error(request, "Booking end time must be after the start time.")
        return redirect("resources:instruments")

    # DSA Interval Overlap Algorithm:
    # A conflict exists if an existing confirmed booking starts before the new end_time
    # AND ends after the new start_time:
    with transaction.atomic():
        # Lock the instrument row so simultaneous requests serialize on SQL Server.
        instrument = Instrument.objects.select_for_update().get(pk=instrument.pk)
        if not instrument.is_active or instrument.status in (
            Instrument.STATUS_MAINTENANCE,
            Instrument.STATUS_RETIRED,
        ):
            messages.error(request, "This instrument is not currently available for booking.")
            return redirect("resources:instruments")
        active_statuses = [
            InstrumentBooking.STATUS_PENDING,
            InstrumentBooking.STATUS_APPROVED,
            InstrumentBooking.STATUS_ISSUED,
        ]
        has_conflict = InstrumentBooking.objects.filter(
            instrument=instrument,
            status__in=active_statuses,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()

        if has_conflict:
            messages.error(
                request,
                f"Scheduling conflict: {instrument.asset_id} is already reserved during that time window. Please select an alternate slot."
            )
            return redirect("resources:instruments")

        booking = InstrumentBooking.objects.create(
            instrument=instrument,
            user=request.user,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
            status=InstrumentBooking.STATUS_PENDING,
        )
        AuditLog.objects.create(
            actor=request.user,
            action="instrument_booking_requested",
            entity_type="InstrumentBooking",
            entity_id=booking.id,
        )

    messages.success(
        request,
        f"Booking request submitted for {instrument.name} ({instrument.asset_id}). It will be available after administrator review.",
    )
    return redirect("resources:instruments")


@login_required
@require_POST
def booking_action(request, pk):
    """Cancel a student's pending booking or approve/reject it as administrator."""
    booking = get_object_or_404(
        InstrumentBooking.objects.select_related("instrument", "user"), pk=pk
    )
    action = request.POST.get("action", "").strip().lower()

    if action == "cancel":
        if booking.user_id != request.user.pk:
            return HttpResponseForbidden("You can only cancel your own booking.")
        if booking.status != InstrumentBooking.STATUS_PENDING:
            messages.error(request, "Only pending bookings can be cancelled.")
            return redirect("resources:instruments")
        next_status = InstrumentBooking.STATUS_CANCELLED
    else:
        if not request.user.is_administrator:
            return HttpResponseForbidden("Only administrators can review bookings.")
        next_status_by_action = {
            "approve": InstrumentBooking.STATUS_APPROVED,
            "reject": InstrumentBooking.STATUS_REJECTED,
        }
        next_status = next_status_by_action.get(action)
        if next_status is None:
            messages.error(request, "Choose a valid booking action.")
            return redirect("resources:instruments")

    with transaction.atomic():
        instrument = Instrument.objects.select_for_update().get(
            pk=booking.instrument_id
        )
        booking = InstrumentBooking.objects.select_for_update().get(pk=booking.pk)
        if booking.status != InstrumentBooking.STATUS_PENDING:
            messages.error(request, "This booking is no longer pending.")
            return redirect("resources:instruments")
        if next_status == InstrumentBooking.STATUS_APPROVED:
            active_statuses = [
                InstrumentBooking.STATUS_APPROVED,
                InstrumentBooking.STATUS_ISSUED,
            ]
            conflict = InstrumentBooking.objects.filter(
                instrument=instrument,
                status__in=active_statuses,
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time,
            ).exclude(pk=booking.pk).exists()
            if conflict:
                messages.error(
                    request,
                    "This booking overlaps another approved reservation and cannot be approved.",
                )
                return redirect("resources:instruments")
        booking.status = next_status
        booking.save(update_fields=["status"])
        action_labels = {
            "approve": "approved",
            "reject": "rejected",
            "cancel": "cancelled",
        }
        AuditLog.objects.create(
            actor=request.user,
            action=f"instrument_booking_{action_labels[action]}",
            entity_type="InstrumentBooking",
            entity_id=booking.pk,
        )
        if action in ("approve", "reject"):
            Notification.objects.create(
                recipient=booking.user,
                actor=request.user,
                verb=(
                    f"Your instrument booking for {instrument.asset_id} was {action_labels[action]}."
                ),
                target_url=reverse("resources:instruments"),
                notif_type=(
                    Notification.NOTIF_SUCCESS
                    if action == "approve"
                    else Notification.NOTIF_WARNING
                ),
            )

    messages.success(request, f"Booking {action_labels[action]}.")
    return redirect("resources:instruments")


@login_required
@require_POST
def issue_booking(request, pk):
    """Record issue of an approved instrument to its student."""
    if not request.user.is_administrator:
        return HttpResponseForbidden("Only administrators can issue equipment.")
    booking = get_object_or_404(InstrumentBooking, pk=pk)
    from django.utils.dateparse import parse_datetime

    due_at = parse_datetime(request.POST.get("due_at", "").strip())
    if due_at is None:
        messages.error(request, "Enter a valid equipment due date and time.")
        return redirect("resources:instruments")
    if timezone.is_naive(due_at):
        due_at = timezone.make_aware(due_at)
    if due_at <= timezone.now():
        messages.error(request, "The due date must be in the future.")
        return redirect("resources:instruments")

    with transaction.atomic():
        booking = InstrumentBooking.objects.select_for_update().select_related(
            "instrument"
        ).get(pk=booking.pk)
        instrument = Instrument.objects.select_for_update().get(
            pk=booking.instrument_id
        )
        if booking.status != InstrumentBooking.STATUS_APPROVED:
            messages.error(request, "Only approved bookings can be issued.")
            return redirect("resources:instruments")
        issue = InstrumentIssue.objects.create(
            booking=booking,
            issued_by=request.user,
            due_at=due_at,
        )
        booking.status = InstrumentBooking.STATUS_ISSUED
        booking.save(update_fields=["status"])
        instrument.status = Instrument.STATUS_IN_USE
        instrument.save(update_fields=["status"])
        AuditLog.objects.create(
            actor=request.user,
            action="instrument_issued",
            entity_type="InstrumentIssue",
            entity_id=issue.pk,
        )

    messages.success(request, f"{instrument.asset_id} was issued to {booking.user.email}.")
    return redirect("resources:instruments")


@login_required
@require_POST
def return_issue(request, pk):
    """Record return condition and close an active instrument issue."""
    if not request.user.is_administrator:
        return HttpResponseForbidden("Only administrators can record equipment returns.")
    return_condition = request.POST.get("return_condition", "").strip()
    if not return_condition or len(return_condition) > 500:
        messages.error(request, "Enter a return condition note (up to 500 characters).")
        return redirect("resources:instruments")

    issue = get_object_or_404(InstrumentIssue, pk=pk)
    with transaction.atomic():
        issue = InstrumentIssue.objects.select_for_update().select_related(
            "booking"
        ).get(pk=issue.pk)
        booking = InstrumentBooking.objects.select_for_update().get(
            pk=issue.booking_id
        )
        instrument = Instrument.objects.select_for_update().get(
            pk=booking.instrument_id
        )
        if issue.returned_at is not None:
            messages.error(request, "This equipment issue has already been returned.")
            return redirect("resources:instruments")
        issue.returned_at = timezone.now()
        issue.returned_by = request.user
        issue.return_condition = return_condition
        issue.save(update_fields=["returned_at", "returned_by", "return_condition"])
        booking.status = InstrumentBooking.STATUS_COMPLETED
        booking.save(update_fields=["status"])
        if instrument.status == Instrument.STATUS_IN_USE:
            instrument.status = Instrument.STATUS_AVAILABLE
            instrument.save(update_fields=["status"])
        AuditLog.objects.create(
            actor=request.user,
            action="instrument_returned",
            entity_type="InstrumentIssue",
            entity_id=issue.pk,
        )

    messages.success(request, f"Return recorded for {instrument.asset_id}.")
    return redirect("resources:instruments")




@login_required
@require_POST
def toggle_bookmark(request, pk):
    """Toggle star / bookmark for an academic lab manual or resource."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_view_resource(request.user, resource):
        return HttpResponseForbidden("Access denied to this resource.")

    bookmark = ResourceBookmark.objects.filter(user=request.user, resource=resource).first()
    if bookmark:
        bookmark.delete()
        messages.info(request, f"Removed '{resource.title}' from your bookmarks.")
    else:
        ResourceBookmark.objects.create(user=request.user, resource=resource)
        messages.success(request, f"Saved '{resource.title}' to your starred resources.")

    next_url = request.POST.get("next", "")
    if not next_url or not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("resources:details", kwargs={"pk": pk})
    return redirect(next_url)


@login_required
def submit_lab_report(request, pk):
    """Submit a completed laboratory experiment report or code solution."""
    resource = get_object_or_404(Resource, pk=pk)
    if not _user_can_view_resource(request.user, resource):
        return HttpResponseForbidden("Access denied to this resource.")

    if request.method != "POST":
        return redirect("resources:details", pk=pk)

    uploaded_file = request.FILES.get("submission_file")
    student_notes = request.POST.get("student_notes", "").strip()

    if not uploaded_file:
        messages.error(request, "Please attach your laboratory report file.")
        return redirect("resources:details", pk=pk)

    try:
        validate_file(uploaded_file, uploaded_file.name, max_size=25 * 1024 * 1024)
    except StorageError as exc:
        messages.error(request, f"Submission rejected: {exc}")
        return redirect("resources:details", pk=pk)

    backend = get_storage_backend()
    storage_key = generate_storage_key(uploaded_file.name)
    sha256 = compute_sha256(uploaded_file)
    file_size = uploaded_file.size

    try:
        backend.save(uploaded_file, uploaded_file.name, storage_key)
    except StorageError as exc:
        messages.error(request, f"Storage upload failed: {exc}")
        return redirect("resources:details", pk=pk)

    with transaction.atomic():
        # Update existing submission or create new
        submission, created = LabSubmission.objects.update_or_create(
            resource=resource,
            student=request.user,
            defaults={
                "original_filename": uploaded_file.name,
                "storage_key": storage_key,
                "file_size_bytes": file_size,
                "sha256_checksum": sha256,
                "student_notes": student_notes,
                "status": LabSubmission.STATUS_SUBMITTED,
                "submitted_at": timezone.now(),
            },
        )

        # Notify the resource owner (instructor/author)
        if resource.uploaded_by and resource.uploaded_by != request.user:
            Notification.objects.create(
                recipient=resource.uploaded_by,
                actor=request.user,
                verb=f"submitted a lab report for '{resource.title}'",
                target_url=reverse("resources:submissions_hub"),
                notif_type=Notification.NOTIF_INFO,
            )

        AuditLog.objects.create(
            actor=request.user,
            action="lab_report_submitted",
            entity_type="LabSubmission",
            entity_id=submission.id,
        )

    messages.success(
        request,
        f"Your report '{uploaded_file.name}' has been successfully submitted (SHA-256: {sha256[:12]}...)."
    )
    return redirect("resources:details", pk=pk)


@login_required
def download_submission(request, pk):
    """Download a student's submitted laboratory report file."""
    submission = get_object_or_404(LabSubmission, pk=pk)
    # Authorization: Student owner or staff/admin or resource author
    can_download = (
        request.user == submission.student
        or request.user.is_administrator
        or (
            request.user.is_faculty
            and request.user == submission.resource.uploaded_by
        )
    )
    if not can_download:
        return HttpResponseForbidden("You are not authorized to download this submission.")

    backend = get_storage_backend()
    file_obj = backend.open(submission.storage_key)
    if file_obj is None:
        raise Http404("Submission file not found on storage server.")

    response = FileResponse(
        file_obj,
        content_type="application/octet-stream",
        as_attachment=True,
        filename=submission.original_filename,
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{submission.original_filename}"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def submissions_hub(request):
    """Central laboratory submission and evaluation hub."""
    status_filter = request.GET.get("status", "").strip()

    if request.user.is_student:
        submissions = LabSubmission.objects.filter(student=request.user).select_related(
            "resource", "reviewed_by"
        )
        if status_filter:
            submissions = submissions.filter(status=status_filter)
        return render(
            request,
            "resources/submissions_hub.html",
            {
                "submissions": submissions,
                "is_faculty": False,
                "status_filter": status_filter,
            },
        )
    elif request.user.is_administrator:
        submissions = LabSubmission.objects.select_related(
            "resource", "student", "reviewed_by"
        ).order_by("-submitted_at")
        if status_filter:
            submissions = submissions.filter(status=status_filter)

        pending_count = LabSubmission.objects.filter(status=LabSubmission.STATUS_SUBMITTED).count()
        reviewed_count = LabSubmission.objects.filter(status=LabSubmission.STATUS_REVIEWED).count()

        return render(
            request,
            "resources/submissions_hub.html",
            {
                "submissions": submissions,
                "is_faculty": True,
                "status_filter": status_filter,
                "pending_count": pending_count,
                "reviewed_count": reviewed_count,
            },
        )
    elif request.user.is_faculty:
        faculty_submissions = LabSubmission.objects.filter(
            resource__uploaded_by=request.user
        ).select_related("resource", "student", "reviewed_by").order_by("-submitted_at")
        submissions = faculty_submissions
        if status_filter:
            submissions = submissions.filter(status=status_filter)

        return render(
            request,
            "resources/submissions_hub.html",
            {
                "submissions": submissions,
                "is_faculty": True,
                "status_filter": status_filter,
                "pending_count": faculty_submissions.filter(
                    status=LabSubmission.STATUS_SUBMITTED
                ).count(),
                "reviewed_count": faculty_submissions.filter(
                    status=LabSubmission.STATUS_REVIEWED
                ).count(),
            },
        )
    return HttpResponseForbidden("Your role cannot access the submission hub.")


@login_required
def grade_submission(request, pk):
    """Faculty reviews and assigns marks/feedback to a student lab submission."""
    submission = get_object_or_404(LabSubmission, pk=pk)
    can_grade = (
        request.user.is_administrator
        or (
            request.user.is_faculty
            and request.user == submission.resource.uploaded_by
        )
    )
    if not can_grade:
        return HttpResponseForbidden("Only instructors or administrators can evaluate lab submissions.")

    if request.method != "POST":
        return redirect("resources:submissions_hub")

    grade_val = request.POST.get("grade", "").strip()
    feedback = request.POST.get("faculty_feedback", "").strip()
    status_val = request.POST.get("status", LabSubmission.STATUS_REVIEWED).strip()

    try:
        grade_num = Decimal(grade_val) if grade_val else None
        if grade_num is not None and (
            not grade_num.is_finite() or grade_num < 0 or grade_num > 100
        ):
            raise ValueError
    except (InvalidOperation, ValueError):
        messages.error(request, "Invalid grade value. Please enter a score between 0 and 100.")
        return redirect("resources:submissions_hub")

    valid_statuses = {choice[0] for choice in LabSubmission.STATUS_CHOICES}
    if status_val not in valid_statuses:
        messages.error(request, "Invalid submission status.")
        return redirect("resources:submissions_hub")

    with transaction.atomic():
        submission.grade = grade_num
        submission.faculty_feedback = feedback
        submission.status = status_val
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=["grade", "faculty_feedback", "status", "reviewed_by", "reviewed_at"])

        Notification.objects.create(
            recipient=submission.student,
            actor=request.user,
            verb=f"evaluated your submission for '{submission.resource.title}' (Marks: {grade_num if grade_num is not None else 'Verified'})",
            target_url=reverse("resources:submissions_hub"),
            notif_type=Notification.NOTIF_SUCCESS if status_val == LabSubmission.STATUS_REVIEWED else Notification.NOTIF_WARNING,
        )

        AuditLog.objects.create(
            actor=request.user,
            action="lab_submission_graded",
            entity_type="LabSubmission",
            entity_id=submission.id,
        )

    messages.success(request, f"Evaluation saved for {submission.student.email}.")
    return redirect("resources:submissions_hub")


def instrument_maintenance_view(request, pk):
    """View and record instrument calibration and maintenance logs."""
    instrument = get_object_or_404(Instrument, pk=pk)
    records = instrument.maintenance_records.select_related("technician").order_by("-performed_date")

    if request.method == "POST":
        if not request.user.is_authenticated or not (request.user.is_administrator or request.user.is_staff):
            return HttpResponseForbidden("Only authorized technicians or faculty can log maintenance.")

        m_type = request.POST.get("maintenance_type", InstrumentMaintenance.TYPE_ROUTINE)
        description = request.POST.get("description", "").strip()
        performed_str = request.POST.get("performed_date", "").strip()
        next_due_str = request.POST.get("next_due_date", "").strip()
        passed = request.POST.get("passed_inspection") == "on"

        from django.utils.dateparse import parse_date

        performed_date = parse_date(performed_str)
        next_due_date = parse_date(next_due_str) if next_due_str else None
        valid_types = {choice[0] for choice in InstrumentMaintenance.TYPE_CHOICES}
        if (
            not description
            or len(description) > 1500
            or m_type not in valid_types
            or performed_date is None
            or (next_due_str and next_due_date is None)
            or (next_due_date and next_due_date < performed_date)
        ):
            messages.error(request, "Please provide description and date performed.")
            return redirect("resources:instrument_maintenance", pk=pk)

        with transaction.atomic():
            InstrumentMaintenance.objects.create(
                instrument=instrument,
                technician=request.user,
                maintenance_type=m_type,
                description=description,
                performed_date=performed_date,
                next_due_date=next_due_date,
                passed_inspection=passed,
            )
            AuditLog.objects.create(
                actor=request.user,
                action="instrument_maintenance_recorded",
                entity_type="Instrument",
                entity_id=instrument.pk,
            )

            # Update instrument condition and status
            instrument.last_calibrated = performed_date
            if passed:
                instrument.status = Instrument.STATUS_AVAILABLE
                instrument.condition = f"Calibrated ({performed_date.strftime('%b %d, %Y')})"
            else:
                instrument.status = Instrument.STATUS_MAINTENANCE
                instrument.condition = "Defect Detected / Pending Repair"
            instrument.save(update_fields=["last_calibrated", "status", "condition"])

        messages.success(request, f"Maintenance record saved for {instrument.asset_id}.")
        return redirect("resources:instrument_maintenance", pk=pk)

    return render(
        request,
        "resources/instrument_maintenance.html",
        {
            "instrument": instrument,
            "records": records,
            "can_manage": request.user.is_authenticated and (request.user.is_administrator or request.user.is_staff),
        },
    )


@login_required
def export_audit_log(request):
    """Export non-repudiation download and access logs for accreditation (ABET / NBA / NAAC)."""
    if not request.user.is_administrator:
        return HttpResponseForbidden("Only administrators can export compliance audit logs.")

    export_format = request.GET.get("format", "csv").lower()
    logs = AccessLog.objects.select_related("user", "resource").order_by("-accessed_at")[:1000]

    if export_format == "json":
        data = [
            {
                "timestamp_utc": log.accessed_at.isoformat(),
                "user_email": log.user.email,
                "resource_id": log.resource.id,
                "resource_title": log.resource.title,
                "ip_address": log.ip_address,
                "sha256": getattr(getattr(log.resource, "resourcefiles", None), "sha256_checksum", None),
            }
            for log in logs
        ]
        response = HttpResponse(json.dumps(data, indent=2), content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="labvault_audit_log.json"'
        return response

    # Standard CSV export
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="labvault_audit_log.csv"'
    writer = csv.writer(response)
    writer.writerow(["Timestamp (UTC)", "User Email", "Resource ID", "Resource Title", "IP Address", "SHA-256 Checksum"])

    for log in logs:
        sha256 = getattr(getattr(log.resource, "resourcefiles", None), "sha256_checksum", "N/A")
        writer.writerow([
            log.accessed_at.strftime("%Y-%m-%d %H:%M:%S"),
            log.user.email,
            log.resource.id,
            log.resource.title,
            log.ip_address or "127.0.0.1",
            sha256,
        ])
    return response


@login_required
def export_equipment_report(request):
    """Export laboratory equipment inventory and utilization report as CSV."""
    if not request.user.is_administrator:
        return HttpResponseForbidden("Only administrators can export equipment reports.")

    instruments = Instrument.objects.prefetch_related("bookings", "maintenance_records").all()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="labvault_equipment_inventory.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Asset ID", "Name", "Model", "Category", "Department", "Location",
        "Status", "Condition", "Last Calibrated", "Total Bookings", "Maintenance Records"
    ])

    for inst in instruments:
        writer.writerow([
            inst.asset_id,
            inst.name,
            inst.model_number,
            inst.category,
            inst.department,
            inst.location,
            inst.get_status_display(),
            inst.condition,
            inst.last_calibrated.strftime("%Y-%m-%d") if inst.last_calibrated else "Not recorded",
            inst.bookings.count(),
            inst.maintenance_records.count(),
        ])
    return response
