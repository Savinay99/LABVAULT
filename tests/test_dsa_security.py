"""Targeted tests for DSA algorithms (SHA-256 hashing) and cybersecurity controls."""

import io
import pytest
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from accounts.models import User
from resources.models import Category, Resource
from resources.storage import compute_sha256, validate_file, StorageError


def test_dsa_sha256_stream_hashing():
    """Verify SHA-256 stream hashing computes correct cryptographic digest."""
    data = b"LabVault Deterministic Academic Resource Content"
    stream = io.BytesIO(data)
    digest = compute_sha256(stream)
    
    import hashlib
    expected = hashlib.sha256(data).hexdigest()
    assert digest == expected
    assert stream.tell() == 0  # Stream pointer must be restored to beginning


def test_file_security_validation_refuses_empty():
    """Verify empty files are rejected."""
    empty_stream = io.BytesIO(b"")
    with pytest.raises(StorageError, match="Empty file"):
        validate_file(empty_stream, "manual.pdf")


def test_file_security_validation_refuses_disallowed_extension():
    """Verify dangerous executable extensions are rejected."""
    stream = io.BytesIO(b"malicious executable payload")
    with pytest.raises(StorageError, match="Unsupported file type"):
        validate_file(stream, "script.exe")


def test_file_security_validation_refuses_oversized_file():
    """Verify oversized files exceeding max_size are rejected."""
    stream = io.BytesIO(b"X" * 1024)
    with pytest.raises(StorageError, match="exceeds the maximum"):
        validate_file(stream, "notes.txt", max_size=512)


@pytest.mark.django_db
def test_authorization_private_resource_access(client):
    """Verify non-owner student cannot view or download another user's private resource."""
    owner = User.objects.create_user(
        username="owner@univ.edu",
        email="owner@univ.edu",
        password="OwnerPassword123!",
    )
    other_student = User.objects.create_user(
        username="other@univ.edu",
        email="other@univ.edu",
        password="OtherPassword123!",
    )
    cat = Category.objects.create(name="Physics Labs")
    private_res = Resource.objects.create(
        title="Confidential Exam Solutions",
        description="Private instructor solutions",
        category=cat,
        uploaded_by=owner,
        visibility=Resource.VISIBILITY_PRIVATE,
        original_filename="solutions.pdf",
        storage_key="dummy_key_12345.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
    )

    # Log in as other student
    client.force_login(other_student)

    # Attempt to view details
    details_url = reverse("resources:details", args=[private_res.pk])
    resp = client.get(details_url)
    assert resp.status_code == 403

    # Attempt to download
    download_url = reverse("resources:download", args=[private_res.pk])
    dl_resp = client.get(download_url)
    assert dl_resp.status_code == 403

