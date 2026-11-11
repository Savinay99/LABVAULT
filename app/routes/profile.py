"""Profile and account settings routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from app.services import auth_service
from app.security import permissions

profile_bp = Blueprint("profile", __name__, template_folder="../../templates")


def _user():
    if not session.get("user_id"):
        from flask import abort
        abort(403)
    return {
        "user_id": session["user_id"],
        "email": session.get("email"),
        "full_name": session.get("full_name"),
        "role": session.get("role"),
    }


@profile_bp.route("/")
def view():
    user = _user()
    return render_template("profile/view.html", user=user)


@profile_bp.route("/settings", methods=["GET", "POST"])
def settings():
    user = _user()
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        try:
            auth_service.change_password(user["user_id"], current_password, new_password)
            flash("Password changed successfully.", "success")
            return redirect(url_for("profile.view"))
        except auth_service.AuthError as exc:
            flash(exc.message, "error")
        except Exception:
            flash("Unable to change password.", "error")
    return render_template("profile/settings.html", user=user)
