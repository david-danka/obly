"""Tests of `obly.db`: connection handling and schema setup."""

import sqlite3
from pathlib import Path

import pytest

from obly.db import connect, create_schema


class Boom(Exception):
    """Raised inside a `connect` block to simulate a failing operation."""


def insert_item(conn: sqlite3.Connection) -> None:
    """Insert one row into the `items` test table.

    Args:
        conn: Connection to a database made by the `db_file` fixture.
    """
    conn.execute("INSERT INTO items (id) VALUES (1)")


def count_items(path: Path) -> int:
    """Count the rows in the `items` test table, using a fresh connection.

    Args:
        path: Path of the database file.

    Returns:
        The number of rows.
    """
    with connect(path) as conn:
        return conn.execute("SELECT count(*) FROM items").fetchone()[0]


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    """Provide a database file with an empty `items` test table.

    The table is independent of the obly schema, so these tests keep
    working when the schema changes.

    Args:
        tmp_path: Per-test temporary directory from pytest.

    Returns:
        Path of the database file.
    """
    path = tmp_path / "test.db"
    with connect(path) as conn:
        conn.execute("CREATE TABLE items (id INTEGER)")
    return path


class TestConnect:
    """Tests of `obly.db.connect`."""

    def test_foreign_keys_are_enabled(self) -> None:
        with connect(":memory:") as conn:
            assert conn.execute("PRAGMA foreign_keys").fetchone() == (1,)

    def test_changes_are_committed_on_success(self, db_file: Path) -> None:
        with connect(db_file) as conn:
            insert_item(conn)
        assert count_items(db_file) == 1

    def test_changes_are_rolled_back_on_error(self, db_file: Path) -> None:
        with pytest.raises(Boom):
            with connect(db_file) as conn:
                insert_item(conn)
                raise Boom
        assert count_items(db_file) == 0

    def test_connection_is_closed_on_success(self) -> None:
        with connect(":memory:") as conn:
            pass
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            conn.execute("SELECT 1")

    def test_connection_is_closed_on_error(self) -> None:
        with pytest.raises(Boom):
            with connect(":memory:") as conn:
                raise Boom
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            conn.execute("SELECT 1")

    def test_old_sqlite_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 36, 0))
        with pytest.raises(RuntimeError, match="3.37.0"):
            with connect(":memory:"):
                pass


class TestCreateSchema:
    """Tests of `obly.db.create_schema`."""

    def test_cannot_be_applied_twice(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.OperationalError, match="already exists"):
            create_schema(db)
