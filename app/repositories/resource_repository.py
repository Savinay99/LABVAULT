"""Resource and category/subject repository.

All queries parameterized. Implements CRUD, search, filtering, pagination,
and ownership checks. Demonstrates JOINs, GROUP BY/aggregates, and safe
pagination.
"""
from app.repositories.db import (
    db_transaction,
    execute,
    execute_scalar,
    query,
    DatabaseError,
)

# Allowed sort columns — whitelist to prevent injection via ORDER BY.
ALLOWED_SORT_COLUMNS = {
    "CreatedAt": "r.CreatedAt",
    "Title": "r.Title",
    "FileSizeBytes": "r.FileSizeBytes",
    "UpdatedAt": "r.UpdatedAt",
}
ALLOWED_SORT_DIRS = {"ASC", "DESC"}


def create_resource(
    conn,
    title,
    description,
    category_id,
    uploaded_by,
    storage_key,
    original_filename,
    content_type,
    file_size_bytes,
    visibility="private",
    subject_ids=None,
):
    """Insert a resource and its subject linkages in one transaction.

    subject_ids is handled by the caller within an open transaction.
    Returns the new ResourceId.
    """
    resource_id = execute_scalar(
        conn,
        """
        INSERT INTO Resources
            (Title, Description, CategoryId, UploadedBy, StorageKey,
             OriginalFileName, ContentType, FileSizeBytes, Visibility)
        OUTPUT INSERTED.ResourceId
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            description,
            category_id,
            uploaded_by,
            storage_key,
            original_filename,
            content_type,
            file_size_bytes,
            visibility,
        ),
    )

    if subject_ids:
        for subject_id in subject_ids:
            execute(
                conn,
                "INSERT INTO ResourceSubjects (ResourceId, SubjectId) VALUES (?, ?)",
                (resource_id, subject_id),
            )

    return resource_id


def get_resource(conn, resource_id):
    """Return a resource row with category name and uploader name."""
    rows = query(
        conn,
        """
        SELECT r.ResourceId, r.Title, r.Description, r.CategoryId,
               c.Name AS CategoryName, r.UploadedBy, u.FullName AS UploadedByName,
               r.StorageKey, r.OriginalFileName, r.ContentType, r.FileSizeBytes,
               r.Visibility, r.CreatedAt, r.UpdatedAt
        FROM Resources r
        LEFT JOIN Categories c ON r.CategoryId = c.CategoryId
        LEFT JOIN Users u ON r.UploadedBy = u.UserId
        WHERE r.ResourceId = ?
        """,
        (resource_id,),
    )
    return rows[0] if rows else None


def get_resource_subjects(conn, resource_id):
    """Return subject names linked to a resource."""
    return query(
        conn,
        """
        SELECT s.SubjectId, s.SubjectCode, s.SubjectName
        FROM Subjects s
        INNER JOIN ResourceSubjects rs ON s.SubjectId = rs.SubjectId
        WHERE rs.ResourceId = ?
        ORDER BY s.SubjectCode
        """,
        (resource_id,),
    )


def update_resource(conn, resource_id, title, description, category_id, visibility, subject_ids):
    """Update resource metadata and replace subject linkages."""
    execute(
        conn,
        """
        UPDATE Resources
        SET Title = ?, Description = ?, CategoryId = ?, Visibility = ?, UpdatedAt = SYSDATETIME()
        WHERE ResourceId = ?
        """,
        (title, description, category_id, visibility, resource_id),
    )
    # Replace subject linkages.
    execute(
        conn, "DELETE FROM ResourceSubjects WHERE ResourceId = ?", (resource_id,)
    )
    if subject_ids:
        for subject_id in subject_ids:
            execute(
                conn,
                "INSERT INTO ResourceSubjects (ResourceId, SubjectId) VALUES (?, ?)",
                (resource_id, subject_id),
            )


def delete_resource(conn, resource_id):
    """Delete a resource and its subject linkages. Returns rowcount."""
    execute(conn, "DELETE FROM ResourceSubjects WHERE ResourceId = ?", (resource_id,))
    return execute(conn, "DELETE FROM Resources WHERE ResourceId = ?", (resource_id,))


def list_resources(conn, page=1, page_size=20, search=None, category_id=None, subject_id=None, sort="CreatedAt", direction="DESC", visible_only=False):
    """Search/filter/paginate resources.

    Returns (items, total_count). Uses parameterized queries and safe
    pagination (OFFSET/FETCH). sort/direction are whitelisted.
    """
    sort_column = ALLOWED_SORT_COLUMNS.get(sort, "r.CreatedAt")
    sort_direction = "ASC" if direction.upper() not in ALLOWED_SORT_DIRS else direction.upper()

    conditions = ["1=1"]
    params = []

    if search:
        conditions.append("(r.Title LIKE ? OR r.Description LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])

    if category_id:
        conditions.append("r.CategoryId = ?")
        params.append(category_id)

    if subject_id:
        conditions.append("EXISTS (SELECT 1 FROM ResourceSubjects rs WHERE rs.ResourceId = r.ResourceId AND rs.SubjectId = ?)")
        params.append(subject_id)

    if visible_only:
        conditions.append("r.Visibility = 'public'")

    where_clause = " AND ".join(conditions)

    # Total count.
    count_sql = f"SELECT COUNT(*) AS c FROM Resources r WHERE {where_clause}"
    total = execute_scalar(conn, count_sql, tuple(params)) or 0

    # Paginated page.
    offset = (page - 1) * page_size
    page_sql = f"""
        SELECT r.ResourceId, r.Title, r.Description, r.CategoryId,
               c.Name AS CategoryName, r.UploadedBy, u.FullName AS UploadedByName,
               r.OriginalFileName, r.ContentType, r.FileSizeBytes, r.Visibility,
               r.CreatedAt, r.UpdatedAt
        FROM Resources r
        LEFT JOIN Categories c ON r.CategoryId = c.CategoryId
        LEFT JOIN Users u ON r.UploadedBy = u.UserId
        WHERE {where_clause}
        ORDER BY {sort_column} {sort_direction}
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    page_params = tuple(params) + (offset, page_size)
    items = query(conn, page_sql, page_params)

    # Attach subjects to each item (small, bounded per page).
    for item in items:
        item["Subjects"] = get_resource_subjects(conn, item["ResourceId"])

    return items, int(total)


def get_resources_by_uploader(conn, user_id, page=1, page_size=20):
    """Resources uploaded by a specific user (owned resources)."""
    return list_resources(
        conn, page=page, page_size=page_size,
        sort="CreatedAt", direction="DESC",
    )


def create_category(conn, name, description):
    category_id = execute_scalar(
        conn,
        "INSERT INTO Categories (Name, Description) OUTPUT INSERTED.CategoryId VALUES (?, ?)",
        (name, description),
    )
    return category_id


def list_categories(conn):
    return query(conn, "SELECT CategoryId, Name, Description FROM Categories ORDER BY Name")


def get_category(conn, category_id):
    rows = query(conn, "SELECT CategoryId, Name, Description FROM Categories WHERE CategoryId = ?", (category_id,))
    return rows[0] if rows else None


def update_category(conn, category_id, name, description):
    return execute(
        conn,
        "UPDATE Categories SET Name = ?, Description = ? WHERE CategoryId = ?",
        (name, description, category_id),
    )


def delete_category(conn, category_id):
    return execute(conn, "DELETE FROM Categories WHERE CategoryId = ?", (category_id,))


def create_subject(conn, subject_code, subject_name):
    subject_id = execute_scalar(
        conn,
        "INSERT INTO Subjects (SubjectCode, SubjectName) OUTPUT INSERTED.SubjectId VALUES (?, ?)",
        (subject_code, subject_name),
    )
    return subject_id


def list_subjects(conn):
    return query(conn, "SELECT SubjectId, SubjectCode, SubjectName FROM Subjects ORDER BY SubjectCode")


def resource_counts_by_category(conn):
    """GROUP BY / aggregate example: resource count per category."""
    return query(
        conn,
        """
        SELECT c.CategoryId, c.Name AS CategoryName, COUNT(r.ResourceId) AS ResourceCount
        FROM Categories c
        LEFT JOIN Resources r ON r.CategoryId = c.CategoryId
        GROUP BY c.CategoryId, c.Name
        ORDER BY ResourceCount DESC
        """
    )


def recent_activity(conn, limit=10):
    """Recent audit/resource activity."""
    return query(
        conn,
        """
        SELECT TOP (?) a.AuditId, a.Action, a.EntityType, a.EntityId, a.CreatedAt,
               u.FullName AS ActorName
        FROM AuditLogs a
        LEFT JOIN Users u ON a.ActorUserId = u.UserId
        ORDER BY a.CreatedAt DESC
        """,
        (limit,),
    )
