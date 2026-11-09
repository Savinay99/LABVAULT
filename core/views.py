"""Core app: landing page and dashboard."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from resources.models import (
    AccessLog,
    InstrumentBooking,
    LabSubmission,
    Resource,
    ResourceBookmark,
    Subject,
)
from accounts.models import User


def _admin_required(view_func):
    from django.core.exceptions import PermissionDenied

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_administrator:
            raise PermissionDenied
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

    pending_submissions_count = 0
    if request.user.is_administrator:
        pending_submissions_count = LabSubmission.objects.filter(status=LabSubmission.STATUS_SUBMITTED).count()

    context = {
        "total_resources": total_resources,
        "user_resources": user_resources,
        "category_counts": category_counts,
        "recent_activity": recent_activity,
        "is_admin": request.user.is_administrator,
        "user_bookmarks": user_bookmarks,
        "user_submissions": user_submissions,
        "user_bookings": user_bookings,
        "pending_submissions_count": pending_submissions_count,
    }
    return render(request, "dashboard/index.html", context)


@login_required
@_admin_required
def admin_dashboard(request):
    """Administrator overview: platform-wide stats and recent activity."""
    total_resources = Resource.objects.count()
    total_users = User.objects.count()
    admin_users = User.objects.filter(role=User.ROLE_ADMIN).count()
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
        "student_users": student_users,
        "total_downloads": total_downloads,
        "recent_resources": recent_resources,
        "recent_downloads": recent_downloads,
        "recent_users": recent_users,
        "category_counts": category_counts,
    }
    return render(request, "admin/dashboard.html", context)
