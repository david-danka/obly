"""Tests of the `accounts` table."""

import re
import sqlite3

import pytest

from text_cases import PADDING, WHITESPACE

# The format of `created_at`: ISO 8601 in UTC, with milliseconds.
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")


@pytest.fixture
def db(db: sqlite3.Connection) -> sqlite3.Connection:
    """Extend the shared `db` fixture with the currency accounts use.

    Args:
        db: The shared fixture's connection, with the schema applied.

    Returns:
        The same connection, with a `HUF` row in `currencies`.
    """
    db.execute(
        """
        INSERT INTO currencies
        VALUES ('HUF', 'Forint', 2, 'Ft')
        """
    )
    return db


def add_account(
    db: sqlite3.Connection,
    name: object = "Wallet",
    kind: object = "checking",
    currency_code: object = "HUF",
    **columns: object,
) -> int:
    """Insert one row into `accounts`.

    Every named argument has a valid sample value, so a test only passes
    the one it wants to break. Columns not passed at all, such as
    `is_archived` and `created_at`, get the table's `DEFAULT`s. The
    values are typed `object` because tests pass deliberately invalid
    types.

    Args:
        db: Connection with the schema applied and a `HUF` currency.
        name: Value for the `name` column.
        kind: Value for the `kind` column.
        currency_code: Value for the `currency_code` column.
        **columns: Values for any other columns, by column name.

    Returns:
        The `id` of the new row.
    """
    values = {
        "name": name,
        "kind": kind,
        "currency_code": currency_code,
        **columns,
    }
    names = ", ".join(values)
    placeholders = ", ".join("?" * len(values))
    cursor = db.execute(
        f"INSERT INTO accounts ({names}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def fetch_column(
    db: sqlite3.Connection, account_id: int, column: str
) -> object:
    """Fetch one column of one row from `accounts`.

    Args:
        db: Connection with the schema applied.
        account_id: The `id` of the row.
        column: The name of the column.

    Returns:
        The column's value.
    """
    return db.execute(
        f"SELECT {column} FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()[0]


def test_valid_account_is_stored(db: sqlite3.Connection) -> None:
    account_id = add_account(db)
    row = db.execute(
        """
        SELECT name, kind, currency_code, is_archived
        FROM accounts
        WHERE id = ?
        """,
        (account_id,),
    ).fetchone()
    assert row == ("Wallet", "checking", "HUF", 0)


class TestId:
    """Tests of the `accounts.id` column."""

    def test_deleted_id_is_not_reused(self, db: sqlite3.Connection) -> None:
        add_account(db, name="Wallet")
        deleted_id = add_account(db, name="Bank")
        db.execute("DELETE FROM accounts WHERE id = ?", (deleted_id,))
        new_id = add_account(db, name="Savings")
        assert new_id > deleted_id


class TestName:
    """Tests of the `accounts.name` column."""

    @pytest.mark.parametrize(
        "name",
        [
            pytest.param(None, id="null"),
            pytest.param("", id="empty"),
            *WHITESPACE,
        ],
    )
    def test_blank_is_rejected(
        self, db: sqlite3.Connection, name: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_account(db, name=name)

    @pytest.mark.parametrize("whitespace", WHITESPACE)
    @pytest.mark.parametrize("template", PADDING)
    def test_surrounding_whitespace_is_rejected(
        self, db: sqlite3.Connection, template: str, whitespace: str
    ) -> None:
        name = template.format(whitespace=whitespace, value="Wallet")
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_account(db, name=name)

    def test_inner_whitespace_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        account_id = add_account(db, name="Daily Spending")
        assert fetch_column(db, account_id, "name") == "Daily Spending"

    def test_max_length_is_accepted(self, db: sqlite3.Connection) -> None:
        account_id = add_account(db, name="x" * 100)
        assert fetch_column(db, account_id, "name") == "x" * 100

    def test_over_max_length_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_account(db, name="x" * 101)

    @pytest.mark.parametrize(
        "duplicate",
        [
            pytest.param("Wallet", id="same_case"),
            pytest.param("WALLET", id="upper_case"),
            pytest.param("wallet", id="lower_case"),
        ],
    )
    def test_duplicate_is_rejected(
        self, db: sqlite3.Connection, duplicate: str
    ) -> None:
        add_account(db, name="Wallet")
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_account(db, name=duplicate)

    def test_archived_account_keeps_its_name(
        self, db: sqlite3.Connection
    ) -> None:
        add_account(db, name="Wallet", is_archived=1)
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_account(db, name="Wallet")

    def test_non_ascii_case_variant_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        # Known gap: COLLATE NOCASE only folds ASCII letters, so the app
        # must catch duplicates like these with str.casefold().
        add_account(db, name="Számla")
        add_account(db, name="SZÁMLA")
        count = db.execute("SELECT count(*) FROM accounts").fetchone()[0]
        assert count == 2


class TestKind:
    """Tests of the `accounts.kind` column."""

    @pytest.mark.parametrize(
        "kind",
        [
            pytest.param("cash", id="single_word"),
            pytest.param("credit_card", id="with_underscore"),
            pytest.param("x" * 50, id="max_length"),
            # The set of types lives in the app, so the schema accepts
            # any well-formed identifier.
            pytest.param("crypto", id="unknown_to_the_app"),
        ],
    )
    def test_well_formed_kind_is_accepted(
        self, db: sqlite3.Connection, kind: str
    ) -> None:
        account_id = add_account(db, kind=kind)
        assert fetch_column(db, account_id, "kind") == kind

    @pytest.mark.parametrize(
        "kind",
        [
            pytest.param("Cash", id="uppercase"),
            pytest.param(" cash", id="surrounding_whitespace"),
            pytest.param("credit card", id="inner_space"),
            pytest.param("_cash", id="leading_underscore"),
            pytest.param("cash2", id="digit"),
            pytest.param("kártya", id="non_ascii"),
            pytest.param("x" * 51, id="over_max_length"),
            pytest.param("", id="empty"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, kind: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="kind"):
            add_account(db, kind=kind)


class TestCurrencyCode:
    """Tests of the `accounts.currency_code` column."""

    def test_null_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="currency_code"):
            add_account(db, currency_code=None)

    def test_unknown_currency_is_rejected(
        self, db: sqlite3.Connection
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            add_account(db, currency_code="AAA")

    def test_currency_in_use_cannot_be_deleted(
        self, db: sqlite3.Connection
    ) -> None:
        add_account(db)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute("DELETE FROM currencies WHERE code = 'HUF'")

    def test_unused_currency_can_be_deleted(
        self, db: sqlite3.Connection
    ) -> None:
        db.execute("INSERT INTO currencies VALUES ('EUR', 'Euro', 2, '€')")
        add_account(db)
        db.execute("DELETE FROM currencies WHERE code = 'EUR'")
        count = db.execute("SELECT count(*) FROM currencies").fetchone()[0]
        assert count == 1


class TestIsArchived:
    """Tests of the `accounts.is_archived` column."""

    def test_defaults_to_not_archived(self, db: sqlite3.Connection) -> None:
        account_id = add_account(db)
        assert fetch_column(db, account_id, "is_archived") == 0

    @pytest.mark.parametrize("is_archived", [0, 1])
    def test_valid_is_accepted(
        self, db: sqlite3.Connection, is_archived: int
    ) -> None:
        account_id = add_account(db, is_archived=is_archived)
        assert fetch_column(db, account_id, "is_archived") == is_archived

    @pytest.mark.parametrize(
        "is_archived",
        [
            pytest.param(2, id="above_one"),
            pytest.param(-1, id="negative"),
            pytest.param(None, id="null"),
            pytest.param("yes", id="text"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, is_archived: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="is_archived"):
            add_account(db, is_archived=is_archived)


class TestCreatedAt:
    """Tests of the `accounts.created_at` column."""

    def test_defaults_to_utc_timestamp(self, db: sqlite3.Connection) -> None:
        account_id = add_account(db)
        created_at = fetch_column(db, account_id, "created_at")
        assert isinstance(created_at, str)
        assert TIMESTAMP.fullmatch(created_at)

    def test_valid_timestamp_is_accepted(self, db: sqlite3.Connection) -> None:
        timestamp = "2026-01-31T23:59:59.999Z"
        account_id = add_account(db, created_at=timestamp)
        assert fetch_column(db, account_id, "created_at") == timestamp

    @pytest.mark.parametrize(
        "created_at",
        [
            pytest.param("yesterday", id="text"),
            pytest.param("2026-01-31", id="date_only"),
            pytest.param("2026-01-31T23:59:59Z", id="no_milliseconds"),
            pytest.param("2026-01-31 23:59:59.999", id="no_t_no_z"),
            pytest.param("2026-02-30T00:00:00.000Z", id="impossible_date"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, created_at: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="created_at"):
            add_account(db, created_at=created_at)
