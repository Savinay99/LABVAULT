"""Resource service: business logic for resource CRUD, search, and files.

Coordinates repositories and the storage backend. Enforces authorization.
"""
import os

from app.services.storage_service import (
    get_storage_backend,
    validate_file,
    generate_storage_key,
    StorageError,
)
from app.repositories import resource_repository
from app.repositories.db import db_transaction
from app.security import permissions
from app.repositories import audit_repository


class ResourceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def create_resource(user, title, description, category_id, visibility, subject_ids, file_storage):
    """Create a resource with an uploaded file. user is the session user dict."""
    from app.security.validation import (
        validate_resource_title,
        validate_resource_description,
    )

    title = validate_resource_title(title)
    description = validate_resource_description(description)
    visibility = visibility or "private"
    if visibility not in ("private", "public"):
        raise ResourceError("Invalid visibility.")

    category_id = int(category_id)

    file_stream = file_storage.get("stream")
    original_filename = file_storage.get("filename")
    content_type = file_storage.get("content_type")

    ext, mime = validate_file(file_stream, original_filename)
    storage_key = generate_storage_key(original_filename)

    file_stream.seek(0, os.SEEK_END)
    file_size_bytes = file_stream.tell()
    file_stream.seek(0)

    try:
        backend = get_storage_backend()
        backend.save(file_stream, original_filename, storage_key)
    except StorageError as exc:
        raise ResourceError(str(exc))

    try:
        with db_transaction() as conn:
            resource_id = resource_repository.create_resource(
                conn,
                title=title,
                description=description,
                category_id=category_id,
                uploaded_by=user["user_id"],
                storage_key=storage_key,
                original_filename=original_filename,
                content_type=mime,
                file_size_bytes=file_size_bytes,
                visibility=visibility,
                subject_ids=subject_ids or [],
            )
            audit_repository.create_audit_log(
                conn, user["user_id"], "CREATE_RESOURCE", "Resource", resource_id
            )
    except Exception:
        # Roll back the file if the DB insert failed to avoid orphans.
        try:
            get_storage_backend().delete(storage_key)
        except Exception:
            pass
        raise

    return resource_id


def get_resource(user, resource_id):
    """Return a resource if authorized. Enforces ownership/visibility."""
    with db_transaction() as conn:
        resource = resource_repository.get_resource(conn, resource_id)
    if resource is None:
        raise ResourceError("Resource not found.", status_code=404)

    is_owner = str(user["user_id"]) == str(resource["UploadedBy"])
    is_admin = user["role"] == permissions.ROLE_ADMIN

    if resource["Visibility"] == "private" and not (is_owner or is_admin):
        raise ResourceError("Access denied to this resource.", status_code=403)

    return resource


def update_resource(user, resource_id, title, description, category_id, visibility, subject_ids):
    """Update metadata if authorized."""
    from app.security.validation import validate_resource_title, validate_resource_description

    title = validate_resource_title(title)
    description = validate_resource_description(description)

    with db_transaction() as conn:
        resource = resource_repository.get_resource(conn, resource_id)
    if resource is None:
        raise ResourceError("Resource not found.", status_code=404)

    is_owner = str(user["user_id"]) == str(resource["UploadedBy"])
    is_admin = user["role"] == permissions.ROLE_ADMIN
    if not (is_owner or is_admin):
        raise ResourceError("Access denied.", status_code=403)

    with db_transaction() as conn:
        resource_repository.update_resource(
            conn, resource_id, title, description, category_id, visibility,
            subject_ids or [],
        )
        audit_repository.create_audit_log(
            conn, user["user_id"], "UPDATE_RESOURCE", "Resource", resource_id
        )


def delete_resource(user, resource_id):
    """Delete a resource and its file if authorized."""
    with db_transaction() as conn:
        resource = resource_repository.get_resource(conn, resource_id)
    if resource is None:
        raise ResourceError("Resource not found.", status_code=404)

    is_owner = str(user["user_id"]) == str(resource["UploadedBy"])
    is_admin = user["role"] == permissions.ROLE_ADMIN
    if not (is_owner or is_admin):
        raise ResourceError("Access denied.", status_code=403)

    storage_key = resource.get("StorageKey")
    with db_transaction() as conn:
        resource_repository.delete_resource(conn, resource_id)
        audit_repository.create_audit_log(
            conn, user["user_id"], "DELETE_RESOURCE", "Resource", resource_id
        )
    # Best-effort file cleanup after DB delete.
    if storage_key:
        try:
            get_storage_backend().delete(storage_key)
        except Exception:
            pass


def list_resources(user, page, page_size, search, category_id, subject_id, sort, direction):
    """List resources the user may see (owned + public + admin all)."""
    with db_transaction() as conn:
        if user["role"] == permissions.ROLE_ADMIN:
            items, total = resource_repository.list_resources(
                conn, page=page, page_size=page_size, search=search,
                category_id=category_id, subject_id=subject_id,
                sort=sort, direction=direction,
            )
        else:
            # Students see public resources plus their own.
            items, total = _list_student_resources(
                conn, user["user_id"], page, page_size, search, category_id,
                subject_id, sort, direction,
            )
    return items, total


def _list_student_resources(conn, user_id, page, page_size, search, category_id, subject_id, sort, direction):
    from app.repositories.db import execute_scalar
    # UNION of public resources and the user's own resources, then paginate.
    # Simpler approach: fetch with a broader query then filter in Python for
    # correctness (bounded by page size). Keep DB doing the heavy filtering.
    base_conditions = ["1=1"]
    params = []
    if search:
        base_conditions.append("(r.Title LIKE ? OR r.Description LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])
    if category_id:
        base_conditions.append("r.CategoryId = ?")
        params.append(category_id)
    if subject_id:
        base_conditions.append(
            "EXISTS (SELECT 1 FROM ResourceSubjects rs WHERE rs.ResourceId = r.ResourceId AND rs.SubjectId = ?)"
        )
        params.append(subject_id)

    where_clause = " AND ".join(base_conditions)
    sql = f"""
        SELECT r.ResourceId, r.Title, r.Description, r.CategoryId,
               c.Name AS CategoryName, r.UploadedBy, u.FullName AS UploadedByName,
               r.OriginalFileName, r.ContentType, r.FileSizeBytes, r.Visibility,
               r.CreatedAt, r.UpdatedAt
        FROM Resources r
        LEFT JOIN Categories c ON r.CategoryId = c.CategoryId
        LEFT JOIN Users u ON r.UploadedBy = u.UserId
        WHERE {where_clause}
          AND (r.Visibility = 'public' OR r.UploadedBy = ?)
    """
    params.append(user_id)
    count_sql = f"SELECT COUNT(*) AS c FROM Resources r WHERE {where_clause} AND (r.Visibility = 'public' OR r.UploadedBy = ?)"
    total = execute_scalar(conn, count_sql, tuple(params)) or 0

    from app.repositories.resource_repository import ALLOWED_SORT_COLUMNS, ALLOWED_SORT_DIRS
    sort_column = ALLOWED_SORT_COLUMNS.get(sort, "r.CreatedAt")
    sort_direction = "ASC" if direction.upper() not in ALLOWED_SORT_DIRS else direction.upper()
    offset = (page - 1) * page_size
    page_sql = sql + f" ORDER BY {sort_column} {sort_direction} OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    items = resource_repository.query(conn, page_sql, tuple(params) + (offset, page_size))
    for item in items:
        item["Subjects"] = resource_repository.get_resource_subjects(conn, item["ResourceId"])
    return items, int(total)
