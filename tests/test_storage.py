"""Tests for storage service: file validation and storage key generation."""
import io
import hashlib
import pytest

from app import create_app
from app.services.storage_service import (
    allowed_extension,
    validate_file,
    generate_storage_key,
    StorageError,
)
from resources.storage import compute_sha256


@pytest.fixture
def app_ctx():
    app = create_app("testing")
    with app.app_context():
        yield app


def test_allowed_extension_true(app_ctx):
    assert allowed_extension("report.pdf") is True
    assert allowed_extension("notes.docx") is True


def test_allowed_extension_false(app_ctx):
    assert allowed_extension("script.exe") is False
    assert allowed_extension("shell.bat") is False
    assert allowed_extension("noext") is False


def test_validate_file_rejects_unsupported(app_ctx):
    stream = io.BytesIO(b"%PDF-1.4 fake")
    with pytest.raises(StorageError):
        validate_file(stream, "malware.exe")


def test_validate_file_rejects_empty(app_ctx):
    stream = io.BytesIO(b"")
    with pytest.raises(StorageError):
        validate_file(stream, "empty.pdf")


def test_validate_file_pdf_signature(app_ctx):
    stream = io.BytesIO(b"%PDF-1.4 content")
    ext, mime = validate_file(stream, "report.pdf")
    assert ext == "pdf"
    assert mime == "application/pdf"


def test_generate_storage_key_unpredictable():
    k1 = generate_storage_key("report.pdf")
    k2 = generate_storage_key("report.pdf")
    assert k1 != k2
    assert k1.endswith(".pdf")
    assert len(k1) > 20


def test_compute_sha256_deterministic():
    content = b"lab manual contents"
    stream = io.BytesIO(content)
    digest = compute_sha256(stream)
    assert digest == hashlib.sha256(content).hexdigest()
    assert len(digest) == 64


def test_compute_sha256_chunks_dont_match_partial():
    # Different content must produce a different digest.
    a = compute_sha256(io.BytesIO(b"hello"))
    b = compute_sha256(io.BytesIO(b"world"))
    assert a != b


def test_compute_sha256_leaves_stream_at_start():
    stream = io.BytesIO(b"data")
    _ = compute_sha256(stream)
    assert stream.read() == b"data"
