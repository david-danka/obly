"""Tests of the `transactions` table."""

import re
import sqlite3

import pytest

from text_cases import PADDING, WHITESPACE

# The format of `created_at`: ISO 8601 in UTC, with milliseconds.
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")

# Rows the `db` fixture below inserts for transactions to point at.
WALLET = 1
BANK = 2
FOOD = 1
SALARY = 2


@pytest.fixture
def db(db: sqlite3.Connection) -> sqlite3.Connection:
    """Extend the shared `db` fixture with accounts and categories.

    Args:
        db: The shared fixture's connection, with the schema applied.

    Returns:
        The same connection, with a `HUF` currency, the accounts `WALLET`
        and `BANK`, the expense category `FOOD` and the income category
        `SALARY`.
    """
    db.execute(
        """
        INSERT INTO currencies
        VALUES ('HUF', 'Forint', 2, 'Ft')
        """
    )
    db.executemany(
        """
        INSERT INTO accounts (id, name, kind, currency_code)
        VALUES (?, ?, ?, 'HUF')
        """,
        [
            (WALLET, "Wallet", "cash"),
            (BANK, "Bank", "checking"),
        ],
    )
    db.executemany(
        "INSERT INTO categories (id, name, kind) VALUES (?, ?, ?)",
        [
            (FOOD, "Food", "expense"),
            (SALARY, "Salary", "income"),
        ],
    )
    return db


def add_transaction(
    db: sqlite3.Connection,
    amount: object = -5000,
    account_id: object = WALLET,
    category_id: object = FOOD,
    occurred_on: object = "2026-10-01",
    **columns: object,
) -> int:
    """Insert one row into `transactions`.

    Every named argument has a valid sample value: by default, a regular
    expense from the wallet. A test only passes the one it wants to break.
    Columns not passed at all, such as `kind`, `note` and `created_at`, get
    the table's `DEFAULT`s. The values are typed `object` because tests
    pass deliberately invalid types.

    Args:
        db: Connection with the rows of the `db` fixture.
        amount: Value for the `amount` column.
        account_id: Value for the `account_id` column.
        category_id: Value for the `category_id` column.
        occurred_on: Value for the `occurred_on` column.
        **columns: Values for any other columns, by column name.

    Returns:
        The `id` of the new row.
    """
    values = {
        "amount": amount,
        "account_id": account_id,
        "category_id": category_id,
        "occurred_on": occurred_on,
        **columns,
    }
    names = ", ".join(values)
    placeholders = ", ".join("?" * len(values))
    cursor = db.execute(
        f"INSERT INTO transactions ({names}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def add_opening_balance(
    db: sqlite3.Connection,
    amount: int = 200_000,
    account_id: int = WALLET,
    occurred_on: str = "2026-01-01",
) -> int:
    """Insert an account's opening balance into `transactions`.

    Args:
        db: Connection with the rows of the `db` fixture.
        amount: The money the account held when tracking began.
        account_id: The account the opening balance belongs to.
        occurred_on: The date tracking began.

    Returns:
        The `id` of the new row.
    """
    return add_transaction(
        db,
        amount=amount,
        account_id=account_id,
        category_id=None,
        occurred_on=occurred_on,
        kind="opening_balance",
    )


def fetch_column(
    db: sqlite3.Connection, transaction_id: int, column: str
) -> object:
    """Fetch one column of one row from `transactions`.

    Args:
        db: Connection with the schema applied.
        transaction_id: The `id` of the row.
        column: The name of the column.

    Returns:
        The column's value.
    """
    return db.execute(
        f"SELECT {column} FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()[0]


def set_column(
    db: sqlite3.Connection, transaction_id: int, column: str, value: object
) -> None:
    """Change one column of one row in `transactions`.

    Args:
        db: Connection with the schema applied.
        transaction_id: The `id` of the row.
        column: The name of the column.
        value: The new value.
    """
    db.execute(
        f"UPDATE transactions SET {column} = ? WHERE id = ?",
        (value, transaction_id),
    )


def test_valid_transaction_is_stored(db: sqlite3.Connection) -> None:
    transaction_id = add_transaction(db)
    row = db.execute(
        """
        SELECT account_id, kind, category_id, occurred_on, amount, note
        FROM transactions
        WHERE id = ?
        """,
        (transaction_id,),
    ).fetchone()
    assert row == (WALLET, "regular", FOOD, "2026-10-01", -5000, None)


def test_balance_is_the_sum_of_amounts(db: sqlite3.Connection) -> None:
    add_opening_balance(db, amount=200_000)
    add_transaction(db, amount=-5000, category_id=FOOD)
    add_transaction(db, amount=1200, category_id=FOOD, note="Refund")
    add_transaction(db, amount=450_000, category_id=SALARY)
    balance = db.execute(
        "SELECT sum(amount) FROM transactions WHERE account_id = ?",
        (WALLET,),
    ).fetchone()[0]
    assert balance == 646_200


class TestId:
    """Tests of the `transactions.id` column."""

    def test_deleted_id_is_not_reused(self, db: sqlite3.Connection) -> None:
        add_transaction(db)
        deleted_id = add_transaction(db)
        db.execute("DELETE FROM transactions WHERE id = ?", (deleted_id,))
        new_id = add_transaction(db)
        assert new_id > deleted_id


class TestAccountId:
    """Tests of the `transactions.account_id` column."""

    def test_null_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="account_id"):
            add_transaction(db, account_id=None)

    def test_unknown_account_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            add_transaction(db, account_id=999)

    def test_account_with_transactions_cannot_be_deleted(
        self, db: sqlite3.Connection
    ) -> None:
        add_transaction(db, account_id=WALLET)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute("DELETE FROM accounts WHERE id = ?", (WALLET,))


class TestKind:
    """Tests of the `transactions.kind` column."""

    def test_defaults_to_regular(self, db: sqlite3.Connection) -> None:
        transaction_id = add_transaction(db)
        assert fetch_column(db, transaction_id, "kind") == "regular"

    @pytest.mark.parametrize(
        "kind",
        [
            pytest.param("transfer", id="unknown"),
            pytest.param("Regular", id="wrong_case"),
            pytest.param("", id="empty"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, kind: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="kind"):
            add_transaction(db, kind=kind)


class TestCategoryId:
    """Tests of the `transactions.category_id` column."""

    def test_regular_transaction_needs_a_category(
        self, db: sqlite3.Connection
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="category_id"):
            add_transaction(db, category_id=None)

    def test_opening_balance_must_not_have_a_category(
        self, db: sqlite3.Connection
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="category_id"):
            add_transaction(db, category_id=FOOD, kind="opening_balance")

    def test_unknown_category_is_rejected(
        self, db: sqlite3.Connection
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            add_transaction(db, category_id=999)

    def test_category_with_transactions_cannot_be_deleted(
        self, db: sqlite3.Connection
    ) -> None:
        add_transaction(db, category_id=FOOD)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute("DELETE FROM categories WHERE id = ?", (FOOD,))

    def test_refund_under_an_expense_category_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        transaction_id = add_transaction(db, amount=1200, category_id=FOOD)
        assert fetch_column(db, transaction_id, "amount") == 1200


class TestOccurredOn:
    """Tests of the `transactions.occurred_on` column."""

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
        transaction_id = add_transaction(db, occurred_on=occurred_on)
        assert fetch_column(db, transaction_id, "occurred_on") == occurred_on

    @pytest.mark.parametrize(
        "occurred_on",
        [
            pytest.param("yesterday", id="text"),
            pytest.param("2026-02-30", id="impossible_date"),
            pytest.param("2025-02-29", id="not_a_leap_year"),
            pytest.param("2026-10-01 12:00", id="with_time"),
            pytest.param("2026/10/01", id="slashes"),
            pytest.param("26-10-01", id="two_digit_year"),
            pytest.param("", id="empty"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, occurred_on: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="occurred_on"):
            add_transaction(db, occurred_on=occurred_on)


class TestAmount:
    """Tests of the `transactions.amount` column."""

    @pytest.mark.parametrize(
        "amount",
        [
            pytest.param(-5000, id="money_out"),
            pytest.param(5000, id="money_in"),
        ],
    )
    def test_signed_amount_is_accepted(
        self, db: sqlite3.Connection, amount: int
    ) -> None:
        transaction_id = add_transaction(db, amount=amount)
        assert fetch_column(db, transaction_id, "amount") == amount

    @pytest.mark.parametrize(
        "amount",
        [
            pytest.param(0, id="zero"),
            pytest.param(1.5, id="fraction"),
            pytest.param("five", id="text"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, amount: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="amount"):
            add_transaction(db, amount=amount)


class TestNote:
    """Tests of the `transactions.note` column."""

    def test_is_optional(self, db: sqlite3.Connection) -> None:
        transaction_id = add_transaction(db)
        assert fetch_column(db, transaction_id, "note") is None

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
            add_transaction(db, note=note)

    @pytest.mark.parametrize("whitespace", WHITESPACE)
    @pytest.mark.parametrize("template", PADDING)
    def test_surrounding_whitespace_is_rejected(
        self, db: sqlite3.Connection, template: str, whitespace: str
    ) -> None:
        note = template.format(whitespace=whitespace, value="Lunch")
        with pytest.raises(sqlite3.IntegrityError, match="note"):
            add_transaction(db, note=note)

    def test_inner_whitespace_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        transaction_id = add_transaction(db, note="Lunch with Anna")
        assert fetch_column(db, transaction_id, "note") == "Lunch with Anna"

    def test_max_length_is_accepted(self, db: sqlite3.Connection) -> None:
        transaction_id = add_transaction(db, note="x" * 500)
        assert fetch_column(db, transaction_id, "note") == "x" * 500

    def test_over_max_length_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="note"):
            add_transaction(db, note="x" * 501)


class TestCreatedAt:
    """Tests of the `transactions.created_at` column."""

    def test_defaults_to_utc_timestamp(self, db: sqlite3.Connection) -> None:
        transaction_id = add_transaction(db)
        created_at = fetch_column(db, transaction_id, "created_at")
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
            add_transaction(db, created_at=created_at)


class TestOpeningBalance:
    """Tests of the rules for opening balances."""

    def test_second_opening_balance_is_rejected(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, account_id=WALLET)
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            add_opening_balance(db, account_id=WALLET)

    def test_each_account_can_have_one(self, db: sqlite3.Connection) -> None:
        add_opening_balance(db, account_id=WALLET)
        add_opening_balance(db, account_id=BANK)
        count = db.execute(
            "SELECT count(*) FROM transactions WHERE kind = 'opening_balance'"
        ).fetchone()[0]
        assert count == 2

    def test_negative_opening_balance_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        transaction_id = add_opening_balance(db, amount=-20_000_000)
        assert fetch_column(db, transaction_id, "amount") == -20_000_000

    def test_transaction_before_it_is_rejected(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, occurred_on="2026-01-01")
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            add_transaction(db, occurred_on="2025-12-31")

    def test_transaction_on_the_same_day_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, occurred_on="2026-01-01")
        transaction_id = add_transaction(db, occurred_on="2026-01-01")
        assert fetch_column(db, transaction_id, "occurred_on") == "2026-01-01"

    def test_opening_balance_after_a_transaction_is_rejected(
        self, db: sqlite3.Connection
    ) -> None:
        add_transaction(db, occurred_on="2026-03-01")
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            add_opening_balance(db, occurred_on="2026-04-01")

    def test_opening_balance_before_existing_transactions_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        add_transaction(db, occurred_on="2026-03-01")
        transaction_id = add_opening_balance(db, occurred_on="2026-02-01")
        assert fetch_column(db, transaction_id, "occurred_on") == "2026-02-01"

    def test_transaction_cannot_move_before_it(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, occurred_on="2026-01-01")
        transaction_id = add_transaction(db, occurred_on="2026-02-01")
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            set_column(db, transaction_id, "occurred_on", "2025-12-01")

    def test_opening_balance_cannot_move_after_a_transaction(
        self, db: sqlite3.Connection
    ) -> None:
        opening_id = add_opening_balance(db, occurred_on="2026-01-01")
        add_transaction(db, occurred_on="2026-02-01")
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            set_column(db, opening_id, "occurred_on", "2026-03-01")

    def test_opening_balance_can_move_earlier(
        self, db: sqlite3.Connection
    ) -> None:
        opening_id = add_opening_balance(db, occurred_on="2026-01-01")
        add_transaction(db, occurred_on="2026-02-01")
        set_column(db, opening_id, "occurred_on", "2025-06-01")
        assert fetch_column(db, opening_id, "occurred_on") == "2025-06-01"

    def test_transaction_cannot_move_into_an_account_before_its_start(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, account_id=BANK, occurred_on="2026-05-01")
        transaction_id = add_transaction(
            db, account_id=WALLET, occurred_on="2026-04-01"
        )
        with pytest.raises(sqlite3.IntegrityError, match="opening balance"):
            set_column(db, transaction_id, "account_id", BANK)

    def test_other_accounts_are_unaffected(
        self, db: sqlite3.Connection
    ) -> None:
        add_opening_balance(db, account_id=BANK, occurred_on="2026-05-01")
        transaction_id = add_transaction(
            db, account_id=WALLET, occurred_on="2026-04-01"
        )
        assert fetch_column(db, transaction_id, "account_id") == WALLET

    def test_unrelated_column_can_change(self, db: sqlite3.Connection) -> None:
        opening_id = add_opening_balance(db, amount=200_000)
        add_transaction(db, occurred_on="2026-02-01")
        set_column(db, opening_id, "amount", 250_000)
        assert fetch_column(db, opening_id, "amount") == 250_000
