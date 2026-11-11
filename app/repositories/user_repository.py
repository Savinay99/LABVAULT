"""User repository: persistence for accounts and authentication state.

All queries are parameterized. Password hashes are never logged.
"""
import pyodbc

from app.repositories.db import (
    db_transaction,
    execute,
    execute_scalar,
    query,
    DatabaseError,
)
from app.security.permissions import ROLE_STUDENT, ROLE_ADMIN


def get_by_email(conn, email):
    """Return a user row dict by email, or None."""
    rows = query(
        conn,
        "SELECT UserId, FullName, Email, PasswordHash, Role, IsActive, CreatedAt, UpdatedAt FROM Users WHERE Email = ?",
        (email,),
    )
    return rows[0] if rows else None


def get_by_id(conn, user_id):
    """Return a user row dict by id, or None."""
    rows = query(
        conn,
        "SELECT UserId, FullName, Email, PasswordHash, Role, IsActive, CreatedAt, UpdatedAt FROM Users WHERE UserId = ?",
        (user_id,),
    )
    return rows[0] if rows else None


def create(conn, full_name, email, password_hash, role=ROLE_STUDENT):
    """Insert a new user. Returns the new UserId (IDENTITY)."""
    user_id = execute_scalar(
        conn,
        """
        INSERT INTO Users (FullName, Email, PasswordHash, Role, IsActive)
        OUTPUT INSERTED.UserId
        VALUES (?, ?, ?, ?, 1)
        """,
        (full_name, email, password_hash, role),
    )
    return user_id


def update_password(conn, user_id, password_hash):
    """Update a user's password hash. Returns rowcount."""
    return execute(
        conn,
        "UPDATE Users SET PasswordHash = ?, UpdatedAt = SYSDATETIME() WHERE UserId = ?",
        (password_hash, user_id),
    )


def set_active(conn, user_id, is_active):
    """Activate or deactivate a user account."""
    return execute(
        conn,
        "UPDATE Users SET IsActive = ?, UpdatedAt = SYSDATETIME() WHERE UserId = ?",
        (1 if is_active else 0, user_id),
    )


def list_users(conn):
    """Return all users (without password hashes) for admin management."""
    return query(
        conn,
        "SELECT UserId, FullName, Email, Role, IsActive, CreatedAt FROM Users ORDER BY CreatedAt DESC"
    )


def email_exists(conn, email):
    """Check whether an email is already registered (parameterized)."""
    count = execute_scalar(
        conn,
        "SELECT COUNT(*) FROM Users WHERE Email = ?",
        (email,),
    )
    return bool(count)


def count_by_role(conn, role):
    """Count users by role (aggregation example)."""
    count = execute_scalar(
        conn,
        "SELECT COUNT(*) FROM Users WHERE Role = ? AND IsActive = 1",
        (role,),
    )
    return int(count or 0)
