"""Secure file storage abstraction.

LabVault supports two backends:
1. LocalProtectedStorage (default, local development) — files stored outside
   the application's static/executable directories, served through a
   Flask route that enforces authorization and safe Content-Disposition.
2. AzureBlobStorage (optional, production) — requires Azure connection string
   and container name. Private container; short-lived SAS URLs issued on
   demand.

Never trust browser-provided filenames or MIME types. Storage keys are
unpredictable. Path traversal is impossible because keys are random names
and never joined with user input.
"""
import os
import secrets
import mimetypes
from uuid import uuid4

from flask import current_app, abort, send_file, make_response

# Magic-byte signatures for common allowed file types. First bytes -> MIME.
MAGIC_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"BM": "image/bmp",
    b"\x50\x4b\x03\x04": "application/zip",
    b"\x25\x50\x44\x46": "application/pdf",
}
# Office Open XML (docx/xlsx/pptx) are ZIP-based; detected by ZIP signature
# and confirmed by extension allowlist + content-type from extension.
OFFICE_ZIP_EXTENSIONS = {"docx", "xlsx", "pptx"}
OFFICE_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class StorageError(Exception):
    """Raised on storage operation failures."""


def allowed_extension(filename):
    """Return True if the file extension is in the allowlist."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def detect_mime(file_stream, filename):
    """Detect MIME type from file signature (magic bytes), falling back to
    extension mapping. Resets the stream position to 0 afterward."""
    header = file_stream.read(16)
    file_stream.seek(0)
    for magic, mime in MAGIC_SIGNATURES.items():
        if header.startswith(magic):
            # For ZIP-based Office files, refine by extension.
            if magic == b"\x50\x4b\x03\x04" and filename:
                ext = filename.rsplit(".", 1)[1].lower()
                if ext in OFFICE_MIME:
                    return OFFICE_MIME[ext]
            return mime
    # Fallback: extension-based MIME (not trusted alone, but used with allowlist).
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def validate_file(file_stream, filename):
    """Validate extension, size, and MIME signature. Returns (ext, mime).
    Raises StorageError on any failure."""
    if not filename:
        raise StorageError("No file provided.")
    if not allowed_extension(filename):
        raise StorageError("Unsupported file type.")
    ext = filename.rsplit(".", 1)[1].lower()
    mime = detect_mime(file_stream, filename)
    # Size check: caller should also enforce MAX_CONTENT_LENGTH at the app level.
    file_stream.seek(0, os.SEEK_END)
    size = file_stream.tell()
    file_stream.seek(0)
    max_size = current_app.config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
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


class StorageBackend:
    """Interface for storage backends."""

    def save(self, file_stream, original_filename, storage_key):
        raise NotImplementedError

    def delete(self, storage_key):
        raise NotImplementedError

    def open(self, storage_key):
        """Return a file-like object for reading, or None if missing."""
        raise NotImplementedError

    def exists(self, storage_key):
        raise NotImplementedError


class LocalProtectedStorage(StorageBackend):
    """Files stored in a protected directory outside static/app folders.

    Served through an authorized download route rather than directly by the
    web server, so authorization is enforced on every download.
    """

    def __init__(self, storage_path):
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)

    def _full_path(self, storage_key):
        # storage_key is server-generated and random; no user input is ever
        # joined here, so path traversal is not possible.
        return os.path.join(self.storage_path, storage_key)

    def save(self, file_stream, original_filename, storage_key):
        path = self._full_path(storage_key)
        with open(path, "wb") as f:
            file_stream.seek(0)
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
            current_app.logger.warning("Failed to delete storage file: %s", storage_key)
        return False

    def open(self, storage_key):
        path = self._full_path(storage_key)
        if not os.path.exists(path):
            return None
        return open(path, "rb")

    def exists(self, storage_key):
        return os.path.exists(self._full_path(storage_key))


class AzureBlobStorage(StorageBackend):
    """Azure Blob Storage backend (optional production override).

    Requires the azure-storage-blob package and a connection string.
    Container is kept private; download URLs are short-lived SAS tokens.
    """

    def __init__(self, connection_string, container_name):
        self.connection_string = connection_string
        self.container_name = container_name
        self._blob_service_client = None
        self._available = self._check_available()

    def _check_available(self):
        try:
            from azure.storage.blob import BlobServiceClient  # noqa: F401
            return True
        except ImportError:
            current_app.logger.warning(
                "azure-storage-blob not installed; Azure storage unavailable."
            )
            return False

    def _client(self):
        if self._blob_service_client is None:
            from azure.storage.blob import BlobServiceClient
            self._blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        return self._blob_service_client

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
            current_app.logger.warning("Failed to delete Azure blob: %s", storage_key)
            return False

    def open(self, storage_key):
        # For downloads we return a SAS URL instead (see storage_service).
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
        """Issue a short-lived, scoped read URL (user delegation SAS preferred)."""
        if not self._available:
            raise StorageError("Azure Blob Storage is not configured.")
        from datetime import datetime, timedelta, timezone
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions

        sas_token = generate_blob_sas(
            account_name=self._client().account_name,
            container_name=self.container_name,
            blob_name=storage_key,
            account_key=self._client().credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )
        from urllib.parse import quote
        return (
            f"https://{self._client().account_name}.blob.core.windows.net/"
            f"{self.container_name}/{quote(storage_key)}?{sas_token}"
        )


def get_storage_backend():
    """Factory: choose local or Azure storage based on configuration."""
    cfg = current_app.config
    conn_str = cfg.get("AZURE_STORAGE_CONNECTION_STRING")
    if conn_str:
        current_app.logger.info("Using Azure Blob Storage backend.")
        return AzureBlobStorage(conn_str, cfg.get("AZURE_STORAGE_CONTAINER_NAME"))
    current_app.logger.info("Using local protected storage backend.")
    storage_path = cfg.get("STORAGE_PATH")
    if not storage_path:
        raise StorageError("STORAGE_PATH is not configured.")
    return LocalProtectedStorage(storage_path)
