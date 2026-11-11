"""Authentication routes: registration, login, logout."""
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

from app.services import auth_service
from app.security.validation import is_valid_email, normalize_email

auth_bp = Blueprint("auth", __name__, template_folder="../../templates")


def _is_safe_url(target):
    """Return True only for same-origin, relative redirect targets.

    Rejects absolute URLs (any scheme), protocol-relative URLs, and anything
    with a host component to prevent open redirects.
    """
    if not target:
        return False
    parsed = urlparse(target)
    return (
        parsed.scheme == ""
        and parsed.netloc == ""
        and not target.startswith("//")
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        try:
            if password != confirm:
                raise auth_service.AuthError("Passwords do not match.")
            user = auth_service.register(full_name, email, password)
            auth_service.login_user(session, user)
            flash("Account created successfully. Welcome to LabVault.", "success")
            return redirect(url_for("dashboard.index"))
        except auth_service.AuthError as exc:
            flash(exc.message, "error")
        except Exception:
            # Never expose internals.
            flash("Unable to create account. Please try again.", "error")
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        try:
            user = auth_service.authenticate(email, password)
            auth_service.login_user(session, user)
            flash("Signed in successfully.", "success")
            next_url = request.args.get("next") or url_for("dashboard.index")
            if not _is_safe_url(next_url):
                next_url = url_for("dashboard.index")
            return redirect(next_url)
        except auth_service.AuthError as exc:
            # Generic message regardless of cause; rate limiting note in docs.
            flash(exc.message, "error")
        except Exception:
            flash("Unable to sign in. Please try again.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    auth_service.logout_user(session)
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
