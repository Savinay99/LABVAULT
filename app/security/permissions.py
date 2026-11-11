"""Authorization helpers.

Role-based access control and ownership checks. Access is denied by default;
every protected backend operation must explicitly verify identity, role,
ownership, and requested action.
"""
from flask import session, abort

ROLE_STUDENT = "student"
ROLE_ADMIN = "administrator"


def current_user(session_dict=None):
    """Return the authenticated user dict from the session, or None."""
    data = session_dict if session_dict is not None else session
    if not data.get("user_id"):
        return None
    return {
        "user_id": data.get("user_id"),
        "email": data.get("email"),
        "full_name": data.get("full_name"),
        "role": data.get("role"),
    }


def login_required(view_func):
    """Decorator: require an authenticated user (401 -> 403 for simplicity)."""
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    """Decorator: require an administrator role."""
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None or user["role"] != ROLE_ADMIN:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapper


def require_ownership_or_admin(resource_owner_id):
    """Raise 403 unless the current user owns the resource or is admin."""
    user = current_user()
    if user is None:
        abort(403)
    if user["role"] == ROLE_ADMIN:
        return True
    if str(user["user_id"]) == str(resource_owner_id):
        return True
    abort(403)
