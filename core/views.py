"""Core app: landing page and dashboard."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render
from resources.models import Resource


def landing(request):
    """Public landing page."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "landing.html")


@login_required
def dashboard_view(request):
    """User dashboard with stats and recent activity."""
    total_resources = Resource.objects.count()
    user_resources = Resource.objects.filter(uploaded_by=request.user).count()
    category_counts = (
        Resource.objects.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    recent_activity = Resource.objects.select_related("category", "uploaded_by").order_by("-created_at")[:10]

    context = {
        "total_resources": total_resources,
        "user_resources": user_resources,
        "category_counts": category_counts,
        "recent_activity": recent_activity,
        "is_admin": request.user.is_administrator,
    }
    return render(request, "dashboard/index.html", context)
