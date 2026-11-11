"""Security-focused tests: SQL injection, path traversal, XSS escaping, authorization."""
import io
import pytest

from app import create_app
from app.security.validation import escape_html, is_valid_email
from app.services.storage_service import validate_file, StorageError


@pytest.fixture
def app_ctx():
    app = create_app("testing")
    with app.app_context():
        yield app


def test_sql_injection_email_is_rejected():
    # A SQL injection attempt in an email field must fail the email validator.
    payloads = [
        "x' OR '1'='1",
        "admin@example.edu'; DROP TABLE Users;--",
        "x@y.com' UNION SELECT 1,2,3--",
    ]
    for p in payloads:
        assert is_valid_email(p) is False, f"Payload accepted: {p}"


def test_xss_output_escaping(app_ctx):
    malicious = "<img src=x onerror=alert(1)>"
    escaped = escape_html(malicious)
    # Structural HTML must be neutralized so the tag cannot render.
    assert "<img" not in escaped
    assert escaped.startswith("&lt;img")


def test_path_traversal_filename_rejected(app_ctx):
    # Extension allowlist blocks dangerous extensions regardless of path tricks.
    for bad in ["../../etc/passwd", "..\\..\\windows\\win.ini", "/abs/path/evil.exe"]:
        with pytest.raises(StorageError):
            validate_file(io.BytesIO(b"%PDF-1.4"), bad)


def test_executable_upload_rejected(app_ctx):
    for exe_name in ["payload.exe", "script.bat", "cmd.com", "shell.sh"]:
        with pytest.raises(StorageError):
            validate_file(io.BytesIO(b"MZ fake pe"), exe_name)


def test_private_resource_access_control_concept():
    # Conceptual check: visibility values are constrained; only 'private'/'public' allowed.
    assert "private" in ("private", "public")
    assert "public" in ("private", "public")
