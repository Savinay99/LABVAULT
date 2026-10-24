"""Dashboard routes."""
from flask import Blueprint, render_template, session, redirect, url_for, flash

from app.repositories import resource_repository
from app.repositories.db import db_transaction
from app.repositories.user_repository import count_by_role
from app.security.permissions import login_required

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../../templates")


@dashboard_bp.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard_view"))
    return render_template("landing.html")


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_view():
    from app.repositories.db import db_transaction
    from app.repositories.resource_repository import (
        resource_counts_by_category,
        recent_activity,
    )
    from app.repositories.user_repository import count_by_role

    with db_transaction() as conn:
        total_resources = _count_resources(conn)
        category_counts = resource_counts_by_category(conn)
        activity = recent_activity(conn, limit=10)

    user_role = session.get("role")
    is_admin = user_role == "administrator"
    return render_template(
        "dashboard/index.html",
        total_resources=total_resources,
        category_counts=category_counts,
        activity=activity,
        is_admin=is_admin,
    )


def _count_resources(conn):
    from app.repositories.db import execute_scalar
    return execute_scalar(conn, "SELECT COUNT(*) FROM Resources") or 0
