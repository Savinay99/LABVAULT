"""Input validation and sanitization helpers.

All functions are pure where possible and raise ValueError with a
user-safe message on invalid input. Never log the raw invalid value
itself (it may contain PII or payloads).
"""
import re
from html import escape

# Email normalization: lowercase, trim. RFC 5322 is intentionally not
# fully implemented; a pragmatic, safe pattern is used.
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9.+_-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# Only safe filename characters are permitted for any user-supplied display
# name that may appear in HTML output or filesystem-adjacent contexts.
SAFE_DISPLAY_REGEX = re.compile(r"^[A-Za-z0-9 ._-]{1,120}$")


def normalize_email(email):
    """Return a lowercased, trimmed email or None if missing."""
    if not email or not isinstance(email, str):
        return None
    return email.strip().lower()


def is_valid_email(email):
    normalized = normalize_email(email)
    if not normalized:
        return False
    return bool(EMAIL_REGEX.match(normalized))


def validate_required_string(value, field_name, min_len=1, max_len=255):
    """Validate a required non-empty string. Returns the stripped value."""
    if value is None or not isinstance(value, str):
        raise ValueError(f"{field_name} is required.")
    stripped = value.strip()
    if len(stripped) < min_len:
        raise ValueError(f"{field_name} is too short.")
    if len(stripped) > max_len:
        raise ValueError(f"{field_name} is too long.")
    return stripped


def validate_password(password):
    """Validate a new password. Returns the value if acceptable."""
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if len(password) > 128:
        raise ValueError("Password is too long.")
    return password


def validate_category_name(name):
    return validate_required_string(name, "Category name", min_len=1, max_len=100)


def validate_subject_code(code):
    return validate_required_string(code, "Subject code", min_len=1, max_len=20)


def validate_subject_name(name):
    return validate_required_string(name, "Subject name", min_len=1, max_len=100)


def validate_resource_title(title):
    return validate_required_string(title, "Title", min_len=1, max_len=200)


def validate_resource_description(description):
    if description is None:
        return ""
    if not isinstance(description, str):
        raise ValueError("Description must be text.")
    if len(description) > 2000:
        raise ValueError("Description is too long.")
    return description.strip()


def escape_html(value):
    """Context-appropriate output escaping for HTML."""
    if value is None:
        return ""
    return escape(str(value), quote=True)
