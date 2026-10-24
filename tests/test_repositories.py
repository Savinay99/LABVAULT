"""Repository-level behavior expectations (documented; DB-backed tests require Azure SQL).

These tests exercise repository functions against a fake in-memory connection
where possible, and document that pyodbc/SQL Server integration tests require
a configured Azure SQL Database.
"""
from unittest.mock import patch, MagicMock

import pytest

from app.repositories import user_repository, resource_repository
from app.repositories.db import execute_scalar


class FakeCursor:
    def __init__(self, rows=None, rowcount=1, columns=None):
        # rows: list of tuples matching `columns`
        self._rows = rows or []
        self.rowcount = rowcount
        self.columns = columns or ["col"]
        self.description = [(c,) for c in self.columns]
        self.closed = False
        self.last_sql = None
        self.last_params = None

    def execute(self, sql, params=()):
        self.last_sql = sql
        self.last_params = params

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def close(self):
        self.closed = True


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def test_user_repository_get_by_email_parameterized():
    cursor = FakeCursor(
        rows=[(1, "A", "a@b.edu", "h", "student", 1)],
        columns=["UserId", "FullName", "Email", "PasswordHash", "Role", "IsActive"],
    )
    conn = FakeConn(cursor)
    result = user_repository.get_by_email(conn, "a@b.edu")
    assert result is not None
    assert result["Email"] == "a@b.edu"
    assert cursor.last_params == ("a@b.edu",)


def test_user_repository_email_exists_uses_parameterized_query():
    cursor = FakeCursor(rows=[(1,)], columns=["c"])
    conn = FakeConn(cursor)
    assert user_repository.email_exists(conn, "a@b.edu") is True
    assert cursor.last_params == ("a@b.edu",)


def test_create_resource_uses_parameterized_insert():
    cursor = FakeCursor(rows=[(7,)], columns=["ResourceId"])
    conn = FakeConn(cursor)
    rid = resource_repository.create_resource(
        conn, "T", "D", 1, 5, "key", "f.pdf", "application/pdf", 100, "private"
    )
    assert rid == 7
    assert "VALUES" in cursor.last_sql.upper()
    assert "?" in cursor.last_sql


def test_delete_resource_parameterized():
    cursor = FakeCursor()
    conn = FakeConn(cursor)
    resource_repository.delete_resource(conn, 3)
    assert cursor.last_params == (3,)


def test_execute_scalar_returns_first_column():
    cursor = FakeCursor(rows=[(42,)], columns=["c"])
    conn = FakeConn(cursor)
    assert execute_scalar(conn, "SELECT 42", ()) == 42
