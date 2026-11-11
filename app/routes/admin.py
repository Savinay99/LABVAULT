"""Administration routes (administrator only)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort

from app.services import auth_service
from app.security import permissions
from app.repositories.db import db_transaction
from app.repositories import user_repository, resource_repository, audit_repository

admin_bp = Blueprint("admin", __name__, template_folder="../../templates")


def _require_admin():
    if not session.get("user_id") or session.get("role") != permissions.ROLE_ADMIN:
        abort(403)


@admin_bp.route("/")
def index():
    _require_admin()
    with db_transaction() as conn:
        users = user_repository.list_users(conn)
        from app.repositories.db import execute_scalar
        total_resources = execute_scalar(conn, "SELECT COUNT(*) FROM Resources") or 0
        total_users = execute_scalar(conn, "SELECT COUNT(*) FROM Users") or 0
        activity = audit_repository.list_audit_logs(conn, page=1, page_size=20)[0]
    return render_template(
        "admin/index.html",
        users=users,
        total_resources=total_resources,
        total_users=total_users,
        activity=activity,
    )


@admin_bp.route("/users")
def users():
    _require_admin()
    with db_transaction() as conn:
        users = user_repository.list_users(conn)
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
def toggle_user(user_id):
    _require_admin()
    actor_id = session.get("user_id")
    if str(actor_id) == str(user_id):
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("admin.users"))
    with db_transaction() as conn:
        target = user_repository.get_by_id(conn, user_id)
        if target is None:
            flash("User not found.", "error")
            return redirect(url_for("admin.users"))
        new_active = not target.get("IsActive")
        user_repository.set_active(conn, user_id, new_active)
        audit_repository.create_audit_log(
            conn, actor_id, "TOGGLE_USER", "User", user_id
        )
    flash(f"User {'activated' if new_active else 'deactivated'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/resources")
def resources():
    _require_admin()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    with db_transaction() as conn:
        items, total = resource_repository.list_resources(
            conn, page=page, page_size=page_size, sort="CreatedAt", direction="DESC"
        )
    total_pages = max(1, -(-total // page_size)) if total else 1
    return render_template("admin/resources.html", resources=items, total=total,
                           page=page, page_size=page_size, total_pages=total_pages)


@admin_bp.route("/audit")
def audit():
    _require_admin()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 50))
    with db_transaction() as conn:
        items, total = audit_repository.list_audit_logs(conn, page=page, page_size=page_size)
    total_pages = max(1, -(-total // page_size)) if total else 1
    return render_template("admin/audit.html", logs=items, total=total,
                           page=page, page_size=page_size, total_pages=total_pages)
