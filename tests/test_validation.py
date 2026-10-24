"""Unit tests for input validation (pure functions, no database)."""
from app.security.validation import (
    is_valid_email,
    normalize_email,
    validate_password,
    validate_required_string,
    validate_resource_title,
    validate_resource_description,
    escape_html,
)


def test_normalize_email_lowercases_and_trims():
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_valid_email():
    assert is_valid_email("student@example.edu") is True
    assert is_valid_email("") is False
    assert is_valid_email("not-an-email") is False
    assert is_valid_email("@example.com") is False


def test_password_min_length():
    try:
        validate_password("short")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "8 characters" in str(exc)


def test_required_string_rejects_empty():
    try:
        validate_required_string("", "Field")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_title_validation():
    assert validate_resource_title("Lab Manual") == "Lab Manual"
    try:
        validate_resource_title("")
        assert False
    except ValueError:
        pass


def test_description_truncates_none():
    assert validate_resource_description(None) == ""


def test_escape_html():
    assert escape_html("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
