"""Fixtures shared by all tests."""

import sqlite3
from collections.abc import Generator

import pytest

from obly.db import connect, create_schema


@pytest.fixture
def db() -> Generator[sqlite3.Connection]:
    """Provide a fresh in-memory database with the schema applied.

    Yields:
        A connection opened through `obly.db.connect`, closed after the test.
    """
    with connect(":memory:") as conn:
        create_schema(conn)
        yield conn
