"""SQLite connection handling and schema setup."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

MIN_SQLITE_VERSION = (3, 37, 0)  # STRICT tables


@contextmanager
def connect(path: str | Path) -> Generator[sqlite3.Connection]:
    """Open a SQLite connection with foreign key enforcement enabled.

    The connection commits when the block exits normally, rolls back when
    it exits with an exception, and is closed in both cases.

    Args:
        path: Path of the database file, or ":memory:" for an in-memory
            database.

    Yields:
        The open connection.

    Raises:
        RuntimeError: If the SQLite library is older than
            `MIN_SQLITE_VERSION`, or if foreign key enforcement could not
            be enabled.
    """
    if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
        required = ".".join(map(str, MIN_SQLITE_VERSION))
        raise RuntimeError(
            f"obly needs SQLite {required}+, found {sqlite3.sqlite_version}"
        )
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        if conn.execute("PRAGMA foreign_keys").fetchone() != (1,):
            raise RuntimeError(
                "SQLite foreign key enforcement could not be enabled"
            )
        with conn:
            yield conn
    finally:
        conn.close()


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables in an empty database.

    The schema runs in a single transaction. If it fails, `connect` rolls
    the transaction back when the error leaves its block, so the database
    is left unchanged.

    Args:
        conn: Connection to an empty database.

    Raises:
        sqlite3.OperationalError: If the schema cannot be applied, for
            example because the tables already exist.
    """
    schema = files("obly").joinpath("schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
