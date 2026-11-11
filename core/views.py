"""Core app: landing page and dashboard."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from resources.models import (
    AccessLog,
    InstrumentBooking,
    LabSubmission,
    Resource,
    ResourceBookmark,
    Subject,
)
from accounts.models import User


def _role_access_denied(request, required_role):
    """Render a helpful role mismatch page without weakening access checks."""
    portal = {
        User.ROLE_STUDENT: ("Student", "core:dashboard"),
        User.ROLE_FACULTY: ("Faculty", "core:faculty_dashboard"),
        User.ROLE_ADMIN: ("Administrator", "core:admin_dashboard"),
    }
    role_label, dashboard_name = portal[required_role]
    dashboard_url = reverse(dashboard_name)
    login_url = f"{reverse('accounts:login')}?{urlencode({'next': dashboard_url})}"
    return render(
        request,
        "errors/403.html",
        {
            "current_role": request.user.get_role_display(),
            "current_role_article": "an" if request.user.is_administrator else "a",
            "required_role": role_label,
            "dashboard_url": dashboard_url,
            "switch_login_url": login_url,
        },
        status=403,
    )


def _admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_administrator:
            return _role_access_denied(request, User.ROLE_ADMIN)
        return view_func(request, *args, **kwargs)

    return wrapper


def landing(request):
    """Public landing page with live repository statistics, multi-persona workspaces, and verified assets."""
    total_resources = Resource.objects.count()
    total_subjects = Subject.objects.count()
    total_downloads = AccessLog.objects.count()
    recent_resources = (
        Resource.objects.filter(visibility=Resource.VISIBILITY_PUBLIC)
        .select_related("category", "uploaded_by")
        .prefetch_related("subjects")
        .order_by("-id")[:6]
    )
    recent_logs = (
        AccessLog.objects.filter(resource__visibility=Resource.VISIBILITY_PUBLIC)
        .select_related("resource")
        .order_by("-accessed_at")[:6]
    )

    context = {
        "total_resources": total_resources,
        "total_subjects": total_subjects,
        "total_downloads": total_downloads,
        "recent_resources": recent_resources,
        "recent_logs": recent_logs,
    }
    return render(request, "landing.html", context)


def about_view(request):
    """Institutional About page explaining LabVault's genesis, architecture, and multi-persona value."""
    total_resources = Resource.objects.count()
    total_subjects = Subject.objects.count()
    total_downloads = AccessLog.objects.count()

    context = {
        "total_resources": total_resources,
        "total_subjects": total_subjects,
        "total_downloads": total_downloads,
    }
    return render(request, "about.html", context)


@login_required
def dashboard_view(request):
    """User dashboard with stats, recent activity, bookmarks, and submissions."""
    if request.user.is_administrator:
        return redirect("core:admin_dashboard")
    if request.user.is_faculty:
        return redirect("core:faculty_dashboard")

    total_resources = Resource.objects.count()
    user_resources = Resource.objects.filter(uploaded_by=request.user).count()
    category_counts = (
        Resource.objects.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    recent_activity = Resource.objects.select_related("category", "uploaded_by")
    if not request.user.is_administrator:
        recent_activity = recent_activity.filter(
            Q(visibility=Resource.VISIBILITY_PUBLIC)
            | Q(uploaded_by=request.user)
        )
    recent_activity = recent_activity.order_by("-created_at")[:10]

    user_bookmarks = ResourceBookmark.objects.filter(user=request.user).select_related("resource__category")[:6]
    user_submissions = LabSubmission.objects.filter(student=request.user).select_related("resource")[:6]
    user_bookings = InstrumentBooking.objects.filter(user=request.user).select_related(
        "instrument", "issue"
    )[:4]
    active_booking_count = InstrumentBooking.objects.filter(user=request.user).exclude(
        status__in=[InstrumentBooking.STATUS_CANCELLED, InstrumentBooking.STATUS_REJECTED, InstrumentBooking.STATUS_COMPLETED]
    ).count()
    waiting_submission_count = LabSubmission.objects.filter(
        student=request.user,
        status__in=[LabSubmission.STATUS_SUBMITTED, LabSubmission.STATUS_RESUBMISSION],
    ).count()
    saved_resource_count = ResourceBookmark.objects.filter(user=request.user).count()

    context = {
        "total_resources": total_resources,
        "user_resources": user_resources,
        "category_counts": category_counts,
        "recent_activity": recent_activity,
        "is_admin": request.user.is_administrator,
        "user_bookmarks": user_bookmarks,
        "user_submissions": user_submissions,
        "user_bookings": user_bookings,
        "active_booking_count": active_booking_count,
        "waiting_submission_count": waiting_submission_count,
        "saved_resource_count": saved_resource_count,
    }
    return render(request, "dashboard/index.html", context)


@login_required
def faculty_dashboard(request):
    """Course-resource overview and review queue for a faculty member."""
    if not request.user.is_faculty:
        return _role_access_denied(request, User.ROLE_FACULTY)

    owned_resources = Resource.objects.filter(uploaded_by=request.user)
    submissions = LabSubmission.objects.filter(
        resource__uploaded_by=request.user
    ).select_related("resource", "student")
    context = {
        "owned_resource_count": owned_resources.count(),
        "pending_count": submissions.filter(
            status=LabSubmission.STATUS_SUBMITTED
        ).count(),
        "reviewed_count": submissions.filter(
            status=LabSubmission.STATUS_REVIEWED
        ).count(),
        "student_count": submissions.values("student_id").distinct().count(),
        "recent_resources": owned_resources.select_related("category").order_by(
            "-created_at"
        )[:6],
        "recent_submissions": submissions.order_by("-submitted_at")[:8],
    }
    return render(request, "faculty/dashboard.html", context)


@login_required
@_admin_required
def admin_dashboard(request):
    """Administrator overview: platform-wide stats and recent activity."""
    total_resources = Resource.objects.count()
    total_users = User.objects.count()
    admin_users = User.objects.filter(role=User.ROLE_ADMIN).count()
    faculty_users = User.objects.filter(role=User.ROLE_FACULTY).count()
    student_users = User.objects.filter(role=User.ROLE_STUDENT).count()
    total_downloads = AccessLog.objects.count()

    recent_resources = (
        Resource.objects.select_related("category", "uploaded_by")
        .order_by("-created_at")[:10]
    )
    recent_downloads = (
        AccessLog.objects.select_related("user", "resource")
        .order_by("-accessed_at")[:10]
    )
    recent_users = User.objects.order_by("-date_joined")[:10]

    category_counts = (
        Resource.objects.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    context = {
        "total_resources": total_resources,
        "total_users": total_users,
        "admin_users": admin_users,
        "faculty_users": faculty_users,
        "student_users": student_users,
        "total_downloads": total_downloads,
        "recent_resources": recent_resources,
        "recent_downloads": recent_downloads,
        "recent_users": recent_users,
        "category_counts": category_counts,
    }
    return render(request, "admin/dashboard.html", context)
