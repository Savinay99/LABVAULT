"""Database connection management for LabVault.

Uses pyodbc with Microsoft SQL Server / Azure SQL Database. Connections are
opened per operation and always closed. All queries must be parameterized;
this module provides a context manager that enforces cursor cleanup.

Supports both SQL Authentication (DB_USERNAME/DB_PASSWORD) and Windows
Trusted Connection (DB_TRUSTED_CONNECTION=yes) for local development.
"""
import os
import pyodbc

from app.config import Config


def get_connection_string(override_config=None):
    """Build a pyodbc connection string from configuration.

    Never returns or logs the password portion of the connection string.
    """
    cfg = override_config or Config
    driver = cfg.DB_DRIVER
    server = cfg.DB_SERVER
    database = cfg.DB_DATABASE

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        "TrustServerCertificate=yes",
        "Encrypt=yes",
    ]

    if getattr(cfg, "DB_TRUSTED_CONNECTION", False):
        parts.append("Trusted_Connection=yes")
    else:
        username = cfg.DB_USERNAME
        password = cfg.DB_PASSWORD
        if username:
            parts.append(f"UID={username}")
        if password:
            parts.append(f"PWD={password}")

    return ";".join(parts)


def get_connection(override_config=None):
    """Open a new pyodbc connection.

    The caller is responsible for closing the connection. Prefer using
    `db_transaction` or `query`/`execute` helpers which handle cleanup.
    """
    conn_str = get_connection_string(override_config)
    conn = pyodbc.connect(conn_str, autocommit=False)
    return conn


class DatabaseError(Exception):
    """Raised on database operation failures."""


def query(conn, sql, params=None):
    """Execute a SELECT query and return rows as dictionaries.

    Always parameterized. The cursor is closed before returning.
    """
    if params is None:
        params = ()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows
    finally:
        cursor.close()


def execute(conn, sql, params=None):
    """Execute a non-SELECT statement (INSERT/UPDATE/DELETE).

    Returns the cursor's rowcount. Always parameterized; cursor closed.
    """
    if params is None:
        params = ()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.rowcount
    finally:
        cursor.close()


def execute_scalar(conn, sql, params=None):
    """Execute a statement and return the first column of the first row."""
    if params is None:
        params = ()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        cursor.close()


class db_transaction:
    """Context manager for explicit transaction boundaries.

    Usage:
        with db_transaction() as conn:
            execute(conn, "INSERT ...", params)
            query(conn, "SELECT ...", params)
        # committed automatically on success, rolled back on exception
    """

    def __init__(self, override_config=None):
        self._override_config = override_config
        self.conn = None

    def __enter__(self):
        self.conn = get_connection(self._override_config)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn is None:
            return False
        try:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            self.conn.close()
        # Do not suppress exceptions.
        return False
