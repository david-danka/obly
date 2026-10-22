"""Tests of the `account_entries` view."""

import sqlite3

import pytest

# Rows the `db` fixture below inserts for entries to point at.
CHECKING = 1  # HUF
SAVINGS = 2  # HUF
EURO = 3  # EUR
FOOD = 1  # expense
SALARY = 2  # income


@pytest.fixture
def db(db: sqlite3.Connection) -> sqlite3.Connection:
    """Extend the shared `db` fixture with currencies, accounts, categories.

    Args:
        db: The shared fixture's connection, with the schema applied.

    Returns:
        The same connection, with the currencies `HUF` and `EUR`, the
        accounts `CHECKING` and `SAVINGS` in HUF and `EURO` in EUR, the
        expense category `FOOD` and the income category `SALARY`.
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
    db.executemany(
        """
        INSERT INTO categories (id, name, kind)
        VALUES (?, ?, ?)
        """,
        [
            (FOOD, "Food", "expense"),
            (SALARY, "Salary", "income"),
        ],
    )
    return db


def add_transaction(
    db: sqlite3.Connection,
    account_id: int,
    amount: int,
    category_id: int | None = FOOD,
    kind: str = "regular",
    note: str | None = None,
) -> int:
    """Insert one row into `transactions`, dated 2026-10-01.

    Args:
        db: Connection with the rows of the `db` fixture.
        account_id: The account the money moves into or out of.
        amount: The signed amount, in minor units.
        category_id: The category, or None for an opening balance.
        kind: `regular` or `opening_balance`.
        note: An optional note.

    Returns:
        The `id` of the new row.
    """
    cursor = db.execute(
        """
        INSERT INTO transactions (
            account_id,
            kind,
            category_id,
            occurred_on,
            amount,
            note
        )
        VALUES (?, ?, ?, '2026-10-01', ?, ?)
        """,
        (account_id, kind, category_id, amount, note),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def add_transfer(
    db: sqlite3.Connection,
    from_account_id: int,
    to_account_id: int,
    from_amount: int,
    to_amount: int,
) -> int:
    """Insert one row into `transfers`, dated 2026-10-02.

    Args:
        db: Connection with the rows of the `db` fixture.
        from_account_id: The account the money leaves.
        to_account_id: The account the money arrives in.
        from_amount: What leaves, in minor units of its account.
        to_amount: What arrives, in minor units of its account.

    Returns:
        The `id` of the new row.
    """
    cursor = db.execute(
        """
        INSERT INTO transfers (
            from_account_id,
            to_account_id,
            occurred_on,
            from_amount,
            to_amount
        )
        VALUES (?, ?, '2026-10-02', ?, ?)
        """,
        (from_account_id, to_account_id, from_amount, to_amount),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def balance(db: sqlite3.Connection, account_id: int) -> int:
    """Compute an account's balance from its entries.

    Args:
        db: Connection with the schema applied.
        account_id: The account.

    Returns:
        The sum of the account's amounts, 0 if it has none.
    """
    return db.execute(
        """
        SELECT coalesce(sum(amount), 0)
        FROM account_entries
        WHERE account_id = ?
        """,
        (account_id,),
    ).fetchone()[0]


def entries(db: sqlite3.Connection, account_id: int) -> list[tuple]:
    """Fetch an account's entries, oldest first.

    Args:
        db: Connection with the schema applied.
        account_id: The account.

    Returns:
        One `(occurred_on, amount, kind, category_id,
        counterpart_account_id, transaction_id, transfer_id, note)` tuple
        per entry.
    """
    return db.execute(
        """
        SELECT
            occurred_on,
            amount,
            kind,
            category_id,
            counterpart_account_id,
            transaction_id,
            transfer_id,
            note
        FROM account_entries
        WHERE account_id = ?
        ORDER BY occurred_on, transaction_id, transfer_id
        """,
        (account_id,),
    ).fetchall()


class TestBalance:
    """Tests of balances computed from the view."""

    def test_account_without_money_has_zero_balance(
        self, db: sqlite3.Connection
    ) -> None:
        assert balance(db, CHECKING) == 0

    def test_includes_transactions_and_both_sides_of_transfers(
        self, db: sqlite3.Connection
    ) -> None:
        add_transaction(
            db, CHECKING, 100_000, category_id=None, kind="opening_balance"
        )
        add_transaction(db, CHECKING, -5_000, category_id=FOOD)
        add_transaction(db, CHECKING, 450_000, category_id=SALARY)
        add_transfer(db, CHECKING, SAVINGS, 100_000, 100_000)
        add_transfer(db, SAVINGS, CHECKING, 20_000, 20_000)
        assert balance(db, CHECKING) == 465_000
        assert balance(db, SAVINGS) == 80_000

    def test_transfers_within_one_currency_leave_the_total_unchanged(
        self, db: sqlite3.Connection
    ) -> None:
        add_transaction(db, CHECKING, 450_000, category_id=SALARY)
        add_transfer(db, CHECKING, SAVINGS, 100_000, 100_000)
        add_transfer(db, SAVINGS, CHECKING, 20_000, 20_000)
        total = balance(db, CHECKING) + balance(db, SAVINGS)
        assert total == 450_000


class TestTransactionEntries:
    """Tests of how transactions appear in the view."""

    def test_keep_their_details(self, db: sqlite3.Connection) -> None:
        transaction_id = add_transaction(
            db, CHECKING, -5_000, category_id=FOOD, note="Lunch"
        )
        assert entries(db, CHECKING) == [
            (
                "2026-10-01",
                -5_000,
                "regular",
                FOOD,
                None,
                transaction_id,
                None,
                "Lunch",
            ),
        ]

    def test_opening_balance_keeps_its_kind(
        self, db: sqlite3.Connection
    ) -> None:
        add_transaction(
            db, CHECKING, 100_000, category_id=None, kind="opening_balance"
        )
        [(_, amount, kind, category_id, *_)] = entries(db, CHECKING)
        assert (amount, kind, category_id) == (
            100_000,
            "opening_balance",
            None,
        )


class TestTransferEntries:
    """Tests of how transfers appear in the view."""

    def test_appear_once_on_each_side(self, db: sqlite3.Connection) -> None:
        transfer_id = add_transfer(db, CHECKING, SAVINGS, 10_000, 10_000)
        assert entries(db, CHECKING) == [
            (
                "2026-10-02",
                -10_000,
                "transfer_out",
                None,
                SAVINGS,
                None,
                transfer_id,
                None,
            ),
        ]
        assert entries(db, SAVINGS) == [
            (
                "2026-10-02",
                10_000,
                "transfer_in",
                None,
                CHECKING,
                None,
                transfer_id,
                None,
            ),
        ]

    def test_use_each_accounts_own_amount_between_currencies(
        self, db: sqlite3.Connection
    ) -> None:
        add_transfer(db, CHECKING, EURO, 400_000, 1_000)
        assert balance(db, CHECKING) == -400_000
        assert balance(db, EURO) == 1_000


def test_view_is_read_only(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.OperationalError, match="view"):
        db.execute(
            """
            INSERT INTO account_entries (account_id, occurred_on, amount)
            VALUES (?, '2026-10-01', 1)
            """,
            (CHECKING,),
        )
