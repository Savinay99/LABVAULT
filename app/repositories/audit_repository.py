"""Audit log repository.

Records security-relevant and administrative actions. Actor may be None for
system events.
"""
from app.repositories.db import execute, execute_scalar, query


def create_audit_log(conn, actor_user_id, action, entity_type, entity_id):
    """Insert an audit record. Returns the new AuditId."""
    audit_id = execute_scalar(
        conn,
        """
        INSERT INTO AuditLogs (ActorUserId, Action, EntityType, EntityId)
        OUTPUT INSERTED.AuditId
        VALUES (?, ?, ?, ?)
        """,
        (actor_user_id, action, entity_type, entity_id),
    )
    return audit_id


def list_audit_logs(conn, page=1, page_size=50):
    """Return paginated audit records with actor names."""
    offset = (page - 1) * page_size
    items = query(
        conn,
        """
        SELECT a.AuditId, a.ActorUserId, u.FullName AS ActorName, a.Action,
               a.EntityType, a.EntityId, a.CreatedAt
        FROM AuditLogs a
        LEFT JOIN Users u ON a.ActorUserId = u.UserId
        ORDER BY a.CreatedAt DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
        (offset, page_size),
    )
    total = execute_scalar(conn, "SELECT COUNT(*) FROM AuditLogs") or 0
    return items, int(total)
