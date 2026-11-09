"""Resources app storage backends: local protected storage + Azure Blob Storage."""

import hashlib
import logging
import mimetypes
import os
import secrets
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import SuspiciousOperation

logger = logging.getLogger(__name__)

# Magic-byte signatures for common allowed file types.
MAGIC_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"BM": "image/bmp",
    b"\x25\x50\x44\x46": "application/pdf",
    b"\x50\x4b\x03\x04": "application/zip",
}

OFFICE_ZIP_EXTENSIONS = {"docx", "xlsx", "pptx"}
OFFICE_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "zip",
    "py", "java", "c", "cpp", "h", "js", "html", "css", "json", "md",
    "png", "jpg", "jpeg", "gif", "bmp",
}


class StorageError(Exception):
    """Raised on storage operation failures."""


def allowed_extension(filename):
    """Return True if the file extension is in the allowlist."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def detect_mime(file_stream, filename):
    """Detect MIME type from file signature, falling back to extension mapping."""
    header = file_stream.read(16)
    file_stream.seek(0)
    for magic, mime in MAGIC_SIGNATURES.items():
        if header.startswith(magic):
            if magic == b"\x50\x4b\x03\x04" and filename:
                ext = filename.rsplit(".", 1)[1].lower()
                if ext in OFFICE_MIME:
                    return OFFICE_MIME[ext]
            return mime
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def validate_file(file_stream, filename, max_size=None):
    """Validate extension, size, and MIME signature. Returns (ext, mime)."""
    if not filename:
        raise StorageError("No file provided.")
    if not allowed_extension(filename):
        raise StorageError("Unsupported file type.")
    ext = filename.rsplit(".", 1)[1].lower()
    mime = detect_mime(file_stream, filename)
    if max_size is None:
        max_size = getattr(settings, "MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
    file_stream.seek(0, os.SEEK_END)
    size = file_stream.tell()
    file_stream.seek(0)
    if size == 0:
        raise StorageError("Empty file.")
    if size > max_size:
        raise StorageError("File exceeds the maximum allowed size.")
    return ext, mime


def generate_storage_key(original_filename):
    """Generate an unpredictable storage identifier."""
    ext = ""
    if original_filename and "." in original_filename:
        ext = "." + original_filename.rsplit(".", 1)[1].lower()
    return f"{uuid4().hex}{secrets.token_hex(8)}{ext}"


def compute_sha256(file_stream):
    """Compute the SHA-256 hex digest of a file-like object.

    The stream is read in chunks and left positioned at the start (seek(0))
    so callers can continue using it afterwards.
    """
    sha256 = hashlib.sha256()
    file_stream.seek(0)
    for chunk in iter(lambda: file_stream.read(65536), b""):
        sha256.update(chunk)
    file_stream.seek(0)
    return sha256.hexdigest()


class StorageBackend:
    """Interface for storage backends."""

    def save(self, file_stream, original_filename, storage_key):
        raise NotImplementedError

    def delete(self, storage_key):
        raise NotImplementedError

    def open(self, storage_key):
        raise NotImplementedError

    def download_url(self, storage_key):
        """Return a URL for downloading the object, or None if not supported."""
        return None

    def exists(self, storage_key):
        raise NotImplementedError


class LocalProtectedStorage(StorageBackend):
    """Files stored outside the app directory, served via an authorized view."""

    def __init__(self, storage_path=None):
        self.storage_path = storage_path or getattr(
            settings, "MEDIA_ROOT", os.path.join(os.getcwd(), "storage")
        )
        os.makedirs(self.storage_path, exist_ok=True)

    def _full_path(self, storage_key):
        return os.path.join(self.storage_path, storage_key)

    def save(self, file_stream, original_filename, storage_key):
        path = self._full_path(storage_key)
        file_stream.seek(0)
        with open(path, "wb") as f:
            while True:
                chunk = file_stream.read(65536)
                if not chunk:
                    break
                f.write(chunk)
        return storage_key

    def delete(self, storage_key):
        path = self._full_path(storage_key)
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
        except OSError:
            logger.warning("Failed to delete storage file: %s", storage_key)
        return False

    def open(self, storage_key):
        path = self._full_path(storage_key)
        if not os.path.exists(path):
            return None
        return open(path, "rb")

    def exists(self, storage_key):
        return os.path.exists(self._full_path(storage_key))


class AzureBlobStorage(StorageBackend):
    """Azure Blob Storage backend (optional production override)."""

    def __init__(self, connection_string, container_name):
        self.connection_string = connection_string
        self.container_name = container_name
        self._available = self._check_available()

    def _check_available(self):
        try:
            from azure.storage.blob import BlobServiceClient  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "azure-storage-blob not installed; Azure storage unavailable."
            )
            return False

    def _client(self):
        from azure.storage.blob import BlobServiceClient
        return BlobServiceClient.from_connection_string(self.connection_string)

    def save(self, file_stream, original_filename, storage_key):
        if not self._available:
            raise StorageError("Azure Blob Storage is not configured.")
        file_stream.seek(0)
        container_client = self._client().get_container_client(self.container_name)
        blob_client = container_client.get_blob_client(storage_key)
        blob_client.upload_blob(file_stream, overwrite=True)
        return storage_key

    def delete(self, storage_key):
        if not self._available:
            return False
        try:
            container_client = self._client().get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(storage_key)
            blob_client.delete_blob()
            return True
        except Exception:
            logger.warning("Failed to delete Azure blob: %s", storage_key)
            return False

    def open(self, storage_key):
        raise NotImplementedError("Use download_url for Azure backend.")

    def exists(self, storage_key):
        if not self._available:
            return False
        try:
            container_client = self._client().get_container_client(self.container_name)
            blob_client = container_client.get_blob_client(storage_key)
            return blob_client.exists()
        except Exception:
            return False

    def download_url(self, storage_key, expiry_minutes=30):
        """Issue a short-lived read URL."""
        if not self._available:
            raise StorageError("Azure Blob Storage is not configured.")
        from datetime import datetime, timedelta, timezone
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from urllib.parse import quote

        sas_token = generate_blob_sas(
            account_name=self._client().account_name,
            container_name=self.container_name,
            blob_name=storage_key,
            account_key=self._client().credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )
        return (
            f"https://{self._client().account_name}.blob.core.windows.net/"
            f"{self.container_name}/{quote(storage_key)}?{sas_token}"
        )


def get_storage_backend():
    """Factory: choose Azure or local storage based on configuration."""
    conn_str = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
    if conn_str:
        logger.info("Using Azure Blob Storage backend.")
        return AzureBlobStorage(
            conn_str, getattr(settings, "AZURE_STORAGE_CONTAINER_NAME", "labvault")
        )
    logger.info("Using local protected storage backend.")
    return LocalProtectedStorage()
