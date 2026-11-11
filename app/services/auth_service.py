"""Authentication service.

Handles registration, login, logout, password change, and login attempt
tracking (rate limiting). Passwords are hashed with Werkzeug's secure
password hashing (pbkdf2:sha256 by default). Never logs credentials.
"""
import threading
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from app.config import Config
from app.repositories import user_repository
from app.security import permissions
from app.repositories.db import db_transaction


class AuthError(Exception):
    """Authentication/authorization failure with a safe, user-facing message."""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# In-memory failed-login tracker keyed by normalized email.
# Applies to unknown accounts too, so an attacker cannot distinguish
# "locked out" from "does not exist". Not shared across processes/workers;
# for multi-worker production deployment, back this with Redis or a DB table.
_lock = threading.Lock()
_login_attempts: dict[str, dict] = {}


def _is_locked_out(email: str) -> bool:
    now = datetime.now(timezone.utc)
    record = _login_attempts.get(email)
    if not record:
        return False
    if now - record["first_failure"] > timedelta(seconds=Config.LOGIN_LOCKOUT_SECONDS):
        # Window expired: clear the record so a fresh attempt starts clean.
        _login_attempts.pop(email, None)
        return False
    return record["count"] >= Config.LOGIN_MAX_FAILED_ATTEMPTS


def _record_failure(email: str) -> None:
    now = datetime.now(timezone.utc)
    record = _login_attempts.get(email)
    if record is None or now - record["first_failure"] > timedelta(
        seconds=Config.LOGIN_LOCKOUT_SECONDS
    ):
        _login_attempts[email] = {"count": 1, "first_failure": now}
    else:
        record["count"] += 1


def _clear_attempts(email: str) -> None:
    _login_attempts.pop(email, None)


def register(full_name, email, password):
    """Register a new user. Returns the new user dict."""
    from app.security.validation import (
        validate_required_string,
        is_valid_email,
        validate_password,
        normalize_email,
    )

    full_name = validate_required_string(full_name, "Full name", min_len=2, max_len=100)
    email = normalize_email(email)
    if not is_valid_email(email):
        raise AuthError("Invalid email address.")
    password = validate_password(password)

    with db_transaction() as conn:
        # Prevent duplicate-account race: unique constraint on Email is the
        # authoritative guard; we also pre-check for a friendly message.
        if user_repository.email_exists(conn, email):
            raise AuthError("An account with this email already exists.", status_code=409)
        password_hash = generate_password_hash(password)
        user_id = user_repository.create(conn, full_name, email, password_hash)

    return {
        "user_id": user_id,
        "email": email,
        "full_name": full_name,
        "role": permissions.ROLE_STUDENT,
    }


def authenticate(email, password):
    """Verify credentials. Returns user dict on success, raises AuthError."""
    from app.security.validation import normalize_email, is_valid_email

    email = normalize_email(email)
    if not email or not is_valid_email(email):
        # Generic failure regardless of which input is wrong.
        raise AuthError("Invalid email or password.")
    if not password:
        raise AuthError("Invalid email or password.")

    with _lock:
        if _is_locked_out(email):
            raise AuthError(
                "Too many failed sign-in attempts. Please try again later.",
                status_code=429,
            )

    with db_transaction() as conn:
        user = user_repository.get_by_email(conn, email)

    if user is None:
        # Unknown account: record a failure but give the same message as a
        # wrong password, so enumeration is not possible.
        with _lock:
            _record_failure(email)
        raise AuthError("Invalid email or password.")
    if not user.get("IsActive"):
        raise AuthError("Account is deactivated. Contact support.")
    if not check_password_hash(user["PasswordHash"], password):
        with _lock:
            _record_failure(email)
        raise AuthError("Invalid email or password.")

    # Successful authentication clears any prior failures for this email.
    with _lock:
        _clear_attempts(email)

    return {
        "user_id": user["UserId"],
        "email": user["Email"],
        "full_name": user["FullName"],
        "role": user["Role"],
    }


def change_password(user_id, current_password, new_password):
    """Change a user's password after verifying the current one."""
    from app.security.validation import validate_password

    validate_password(new_password)
    if not current_password:
        raise AuthError("Current password is required.")

    with db_transaction() as conn:
        user = user_repository.get_by_id(conn, user_id)
        if user is None:
            raise AuthError("User not found.", status_code=404)
        if not check_password_hash(user["PasswordHash"], current_password):
            raise AuthError("Current password is incorrect.")
        new_hash = generate_password_hash(new_password)
        user_repository.update_password(conn, user_id, new_hash)

    return True


def login_user(session, user):
    """Store the authenticated user in the session and regenerate the id.

    session is the Flask session object (mapping). Regenerating the session
    identifier mitigates session fixation.
    """
    session.clear()
    session["user_id"] = user["user_id"]
    session["email"] = user["email"]
    session["full_name"] = user["full_name"]
    session["role"] = user["role"]
    session.permanent = True
    # Regenerate session id to mitigate fixation (Flask handles cookie rotation
    # on next response; clearing then setting is the best-effort approach).


def logout_user(session):
    """Clear the session."""
    session.clear()
