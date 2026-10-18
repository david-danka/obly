"""Tests of schema-wide settings."""

import sqlite3


def test_schema_version_is_set(db: sqlite3.Connection) -> None:
    assert db.execute("PRAGMA user_version").fetchone() == (1,)
