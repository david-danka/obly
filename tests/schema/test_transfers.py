"""Tests of the `transfers` table."""

import re
import sqlite3

import pytest

from obly.limits import NOTE_MAX_LENGTH
from text_cases import PADDING, WHITESPACE

# The format of `created_at`: ISO 8601 in UTC, with milliseconds.
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")

# Accounts the `db` fixture below inserts for transfers to point at.
CHECKING = 1  # HUF
SAVINGS = 2  # HUF
EURO = 3  # EUR


@pytest.fixture
def db(db: sqlite3.Connection) -> sqlite3.Connection:
    """Extend the shared `db` fixture with currencies and accounts.

    Args:
        db: The shared fixture's connection, with the schema applied.

    Returns:
        The same connection, with the currencies `HUF` and `EUR`, and the
        accounts `CHECKING` and `SAVINGS` in HUF and `EURO` in EUR.
    """
    db.executemany(
        """
        INSERT INTO currencies (code, name, minor_unit)
        VALUES (?, ?, 2)
        """,
        [
            ("HUF", "Forint"),
            ("EUR", "Euro"),
        ],
    )
    db.executemany(
        """
        INSERT INTO accounts (id, name, kind, currency_code)
        VALUES (?, ?, ?, ?)
        """,
        [
            (CHECKING, "Checking", "checking", "HUF"),
            (SAVINGS, "Savings", "savings", "HUF"),
            (EURO, "Euro account", "checking", "EUR"),
        ],
    )
    return db


def add_transfer(
    db: sqlite3.Connection,
    from_account_id: object = CHECKING,
    to_account_id: object = SAVINGS,
    from_amount: object = 10_000,
    to_amount: object = 10_000,
    occurred_on: object = "2026-10-01",
    **columns: object,
) -> int:
    """Insert one row into `transfers`.

    Every named argument has a valid sample value: by default, 10,000
    from checking to savings, both in HUF. A test only passes the one it
    wants to break. Columns not passed at all, such as `note` and
    `created_at`, get the table's `DEFAULT`s. The values are typed
    `object` because tests pass deliberately invalid types.

    Args:
        db: Connection with the rows of the `db` fixture.
        from_account_id: Value for the `from_account_id` column.
        to_account_id: Value for the `to_account_id` column.
        from_amount: Value for the `from_amount` column.
        to_amount: Value for the `to_amount` column.
        occurred_on: Value for the `occurred_on` column.
        **columns: Values for any other columns, by column name.

    Returns:
        The `id` of the new row.
    """
    values = {
        "from_account_id": from_account_id,
        "to_account_id": to_account_id,
        "from_amount": from_amount,
        "to_amount": to_amount,
        "occurred_on": occurred_on,
        **columns,
    }
    names = ", ".join(values)
    placeholders = ", ".join("?" * len(values))
    cursor = db.execute(
        f"INSERT INTO transfers ({names}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def add_opening_balance(
    db: sqlite3.Connection, account_id: int, occurred_on: str
) -> int:
    """Insert an account's opening balance into `transactions`.

    Args:
        db: Connection with the rows of the `db` fixture.
        account_id: The account the opening balance belongs to.
        occurred_on: The date tracking began.

    Returns:
        The `id` of the new row.
    """
    cursor = db.execute(
        """
        INSERT INTO transactions (account_id, kind, occurred_on, amount)
        VALUES (?, 'opening_balance', ?, 100000)
        """,
        (account_id, occurred_on),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def fetch_column(
    db: sqlite3.Connection, transfer_id: int, column: str
) -> object:
    """Fetch one column of one row from `transfers`.

    Args:
        db: Connection with the schema applied.
        transfer_id: The `id` of the row.
        column: The name of the column.

    Returns:
        The column's value.
    """
    return db.execute(
        f"SELECT {column} FROM transfers WHERE id = ?", (transfer_id,)
    ).fetchone()[0]


def update_transfer(
    db: sqlite3.Connection, transfer_id: int, **columns: object
) -> None:
    """Change columns of one row in `transfers`.

    Args:
        db: Connection with the schema applied.
        transfer_id: The `id` of the row.
        **columns: The new values, by column name.
    """
    assignments = ", ".join(f"{name} = ?" for name in columns)
    db.execute(
        f"UPDATE transfers SET {assignments} WHERE id = ?",
        (*columns.values(), transfer_id),
    )


def test_valid_transfer_is_stored(db: sqlite3.Connection) -> None:
    transfer_id = add_transfer(db)
    row = db.execute(
        """
        SELECT
            from_account_id,
            to_account_id,
            from_amount,
            to_amount,
            occurred_on,
            note
        FROM transfers
        WHERE id = ?
        """,
        (transfer_id,),
    ).fetchone()
    assert row == (CHECKING, SAVINGS, 10_000, 10_000, "2026-10-01", None)


class TestId:
    """Tests of the `transfers.id` column."""

    def test_deleted_id_is_not_reused(self, db: sqlite3.Connection) -> None:
        add_transfer(db)
        deleted_id = add_transfer(db)
        db.execute("DELETE FROM transfers WHERE id = ?", (deleted_id,))
        new_id = add_transfer(db)
        assert new_id > deleted_id


class TestAccounts:
    """Tests of `transfers.from_account_id` and `to_account_id`."""

    @pytest.mark.parametrize(
        "account_column", ["from_account_id", "to_account_id"]
    )
    def test_null_is_rejected(
        self, db: sqlite3.Connection, account_column: str
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match=account_column):
            add_transfer(db, **{account_column: None})

    @pytest.mark.parametrize(
        "account_column", ["from_account_id", "to_account_id"]
    )
    def test_unknown_account_is_rejected(
        self, db: sqlite3.Connection, account_column: str
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            add_transfer(db, **{account_column: 999})

    def test_transfer_to_the_same_account_is_rejected(
        self, db: sqlite3.Connection
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="to_account_id"):
            add_transfer(db, from_account_id=CHECKING, to_account_id=CHECKING)

    @pytest.mark.parametrize("account_id", [CHECKING, SAVINGS])
    def test_account_with_transfers_cannot_be_deleted(
        self, db: sqlite3.Connection, account_id: int
    ) -> None:
        add_transfer(db, from_account_id=CHECKING, to_account_id=SAVINGS)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))


class TestAmounts:
    """Tests of `transfers.from_amount` and `to_amount`."""

    @pytest.mark.parametrize("amount_column", ["from_amount", "to_amount"])
    @pytest.mark.parametrize(
        "amount",
        [
            pytest.param(0, id="zero"),
            pytest.param(-1, id="negative"),
            pytest.param(1.5, id="fraction"),
            pytest.param("ten", id="text"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, amount_column: str, amount: object
    ) -> None:
        # Between currencies, so the equal-amounts rule doesn't fire first.
        with pytest.raises(sqlite3.IntegrityError, match=amount_column):
            add_transfer(db, to_account_id=EURO, **{amount_column: amount})


class TestSameCurrency:
    """Tests of equal amounts for transfers within one currency."""

    def test_unequal_amounts_are_rejected(
        self, db: sqlite3.Connection
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="equal amounts"):
            add_transfer(db, from_amount=10_000, to_amount=9_000)

    def test_unequal_amounts_between_currencies_are_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        transfer_id = add_transfer(
            db, to_account_id=EURO, from_amount=400_000, to_amount=1_000
        )
        assert fetch_column(db, transfer_id, "to_amount") == 1_000

    def test_amount_cannot_become_unequal(
        self, db: sqlite3.Connection
    ) -> None:
        transfer_id = add_transfer(db)
        with pytest.raises(sqlite3.IntegrityError, match="equal amounts"):
            update_transfer(db, transfer_id, to_amount=9_000)

    def test_amount_between_currencies_can_change(
        self, db: sqlite3.Connection
    ) -> None:
        transfer_id = add_transfer(
            db, to_account_id=EURO, from_amount=400_000, to_amount=1_000
        )
        update_transfer(db, transfer_id, to_amount=1_010)
        assert fetch_column(db, transfer_id, "to_amount") == 1_010

    def test_cannot_move_into_one_currency_with_unequal_amounts(
        self, db: sqlite3.Connection
    ) -> None:
        transfer_id = add_transfer(
            db, to_account_id=EURO, from_amount=400_000, to_amount=1_000
        )
        with pytest.raises(sqlite3.IntegrityError, match="equal amounts"):
            update_transfer(db, transfer_id, to_account_id=SAVINGS)


class TestOccurredOn:
    """Tests of the `transfers.occurred_on` column."""

    @pytest.mark.parametrize(
        "occurred_on",
        [
            pytest.param("2026-10-01", id="typical"),
            pytest.param("2024-02-29", id="leap_day"),
        ],
    )
    def test_valid_date_is_accepted(
        self, db: sqlite3.Connection, occurred_on: str
    ) -> None:
        transfer_id = add_transfer(db, occurred_on=occurred_on)
        assert fetch_column(db, transfer_id, "occurred_on") == occurred_on

    @pytest.mark.parametrize(
        "occurred_on",
        [
            pytest.param("yesterday", id="text"),
            pytest.param("2026-02-30", id="impossible_date"),
            pytest.param("2025-02-29", id="not_a_leap_year"),
            pytest.param("2026-10-01 12:00", id="with_time"),
            pytest.param("2026/10/01", id="slashes"),
            pytest.param("", id="empty"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, occurred_on: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="occurred_on"):
            add_transfer(db, occurred_on=occurred_on)


class TestNote:
    """Tests of the `transfers.note` column."""

    def test_is_optional(self, db: sqlite3.Connection) -> None:
        transfer_id = add_transfer(db)
        assert fetch_column(db, transfer_id, "note") is None

    @pytest.mark.parametrize(
        "note",
        [
            pytest.param("", id="empty"),
            *WHITESPACE,
        ],
    )
    def test_blank_is_rejected(
        self, db: sqlite3.Connection, note: str
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="note"):
            add_transfer(db, note=note)

    @pytest.mark.parametrize("whitespace", WHITESPACE)
    @pytest.mark.parametrize("template", PADDING)
    def test_surrounding_whitespace_is_rejected(
        self, db: sqlite3.Connection, template: str, whitespace: str
    ) -> None:
        note = template.format(whitespace=whitespace, value="Rent")
        with pytest.raises(sqlite3.IntegrityError, match="note"):
            add_transfer(db, note=note)

    def test_inner_whitespace_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        transfer_id = add_transfer(db, note="Rent for October")
        assert fetch_column(db, transfer_id, "note") == "Rent for October"

    def test_max_length_is_accepted(self, db: sqlite3.Connection) -> None:
        transfer_id = add_transfer(db, note="x" * NOTE_MAX_LENGTH)
        assert fetch_column(db, transfer_id, "note") == "x" * NOTE_MAX_LENGTH

    def test_over_max_length_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="note"):
            add_transfer(db, note="x" * (NOTE_MAX_LENGTH + 1))


class TestCreatedAt:
    """Tests of the `transfers.created_at` column."""

    def test_defaults_to_utc_timestamp(self, db: sqlite3.Connection) -> None:
        transfer_id = add_transfer(db)
        created_at = fetch_column(db, transfer_id, "created_at")
        assert isinstance(created_at, str)
        assert TIMESTAMP.fullmatch(created_at)

    @pytest.mark.parametrize(
        "created_at",
        [
            pytest.param("yesterday", id="text"),
            pytest.param("2026-01-31", id="date_only"),
            pytest.param("2026-01-31T23:59:59Z", id="no_milliseconds"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, created_at: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="created_at"):
            add_transfer(db, created_at=created_at)


class TestOpeningBalance:
    """Tests of transfers against the accounts' opening balances."""

    @pytest.mark.parametrize("account_id", [CHECKING, SAVINGS])
    def test_transfer_before_it_is_rejected(
        self, db: sqlite3.Connection, account_id: int
    ) -> None:
        add_opening_balance(db, account_id, "2026-05-01")
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            add_transfer(db, occurred_on="2026-04-30")

    def test_transfer_on_the_same_day_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, SAVINGS, "2026-05-01")
        transfer_id = add_transfer(db, occurred_on="2026-05-01")
        assert fetch_column(db, transfer_id, "occurred_on") == "2026-05-01"

    def test_transfer_cannot_move_before_it(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, SAVINGS, "2026-05-01")
        transfer_id = add_transfer(db, occurred_on="2026-06-01")
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            update_transfer(db, transfer_id, occurred_on="2026-04-01")

    def test_transfer_cannot_move_into_an_account_before_its_start(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, EURO, "2026-05-01")
        transfer_id = add_transfer(
            db,
            to_account_id=SAVINGS,
            from_amount=10_000,
            to_amount=10_000,
            occurred_on="2026-04-01",
        )
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            update_transfer(db, transfer_id, to_account_id=EURO, to_amount=25)

    @pytest.mark.parametrize("account_id", [CHECKING, SAVINGS])
    def test_opening_balance_after_a_transfer_is_rejected(
        self, db: sqlite3.Connection, account_id: int
    ) -> None:
        add_transfer(db, occurred_on="2026-10-01")
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            add_opening_balance(db, account_id, "2026-11-01")

    def test_opening_balance_before_a_transfer_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        add_transfer(db, occurred_on="2026-10-01")
        add_opening_balance(db, SAVINGS, "2026-09-01")
        count = db.execute(
            "SELECT count(*) FROM transactions WHERE account_id = ?",
            (SAVINGS,),
        ).fetchone()[0]
        assert count == 1

    def test_opening_balance_cannot_move_after_a_transfer(
        self, db: sqlite3.Connection
    ) -> None:
        opening_id = add_opening_balance(db, SAVINGS, "2026-09-01")
        add_transfer(db, occurred_on="2026-10-01")
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            db.execute(
                "UPDATE transactions SET occurred_on = ? WHERE id = ?",
                ("2026-12-01", opening_id),
            )
