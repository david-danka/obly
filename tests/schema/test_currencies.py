"""Tests of the `currencies` table."""

import sqlite3

import pytest

# The whitespace set the schema's checks strip: tab, LF, CR, space, NBSP.
WHITESPACE = [
    pytest.param("\t",     id="tab"),
    pytest.param("\n",     id="lf"),
    pytest.param("\r",     id="cr"),
    pytest.param(" ",      id="space"),
    pytest.param("\u00a0", id="nbsp"),
]

# Templates that put a whitespace character before or after a value.
PADDING = [
    pytest.param("{whitespace}{value}", id="leading"),
    pytest.param("{value}{whitespace}", id="trailing"),
]


def add_currency(
    db: sqlite3.Connection,
    code: object = "EUR",
    name: object = "Euro",
    minor_unit: object = 2,
    symbol: object = "€",
) -> None:
    """Insert one row into `currencies`.

    Every argument defaults to a valid value, so a test only passes the
    one it wants to break. The values are typed `object` because tests
    pass deliberately invalid types.

    Args:
        db: Connection with the schema applied.
        code: Value for the `code` column.
        name: Value for the `name` column.
        minor_unit: Value for the `minor_unit` column.
        symbol: Value for the `symbol` column.
    """
    db.execute(
        "INSERT INTO currencies (code, name, minor_unit, symbol) "
        "VALUES (?, ?, ?, ?)",
        (code, name, minor_unit, symbol),
    )


def fetch_currency(db: sqlite3.Connection, code: str) -> tuple[object, ...] | None:
    """Fetch one row from `currencies` by its code.

    Args:
        db: Connection with the schema applied.
        code: The currency code to look up.

    Returns:
        The row as `(code, name, minor_unit, symbol)`, or None if no row
        has that code.
    """
    return db.execute(
        "SELECT code, name, minor_unit, symbol "
        "FROM currencies "
        "WHERE code = ?",
        (code,),
    ).fetchone()


def test_valid_currency_is_stored(db: sqlite3.Connection) -> None:
    add_currency(db)
    assert fetch_currency(db, "EUR") == ("EUR", "Euro", 2, "€")


class TestCode:
    """Tests of the `currencies.code` column."""

    @pytest.mark.parametrize("code", [
        pytest.param("eur",  id="lowercase"),
        pytest.param("Eur",  id="mixed_case"),
        pytest.param("EU",   id="too_short"),
        pytest.param("EURO", id="too_long"),
        pytest.param("E1R",  id="contains_digit"),
        pytest.param("",     id="empty"),
        pytest.param(None,   id="null"),
    ])
    def test_invalid_is_rejected(self, db: sqlite3.Connection, code: object) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="code"):
            add_currency(db, code=code)

    def test_duplicate_is_rejected(self, db: sqlite3.Connection) -> None:
        add_currency(db)
        with pytest.raises(sqlite3.IntegrityError, match="code"):
            add_currency(db, name="Euro again")

    def test_well_formed_unknown_is_accepted(self, db: sqlite3.Connection) -> None:
        add_currency(db, code="AAA")
        assert fetch_currency(db, "AAA") is not None


class TestName:
    """Tests of the `currencies.name` column."""

    @pytest.mark.parametrize("name", [
        pytest.param(None, id="null"),
        pytest.param("",   id="empty"),
        *WHITESPACE,
    ])
    def test_blank_is_rejected(self, db: sqlite3.Connection, name: object) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_currency(db, name=name)

    @pytest.mark.parametrize("whitespace", WHITESPACE)
    @pytest.mark.parametrize("template", PADDING)
    def test_surrounding_whitespace_is_rejected(
        self, db: sqlite3.Connection, template: str, whitespace: str
    ) -> None:
        name = template.format(whitespace=whitespace, value="Euro")
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_currency(db, name=name)

    def test_inner_whitespace_is_accepted(self, db: sqlite3.Connection) -> None:
        add_currency(db, code="USD", name="US Dollar")
        assert fetch_currency(db, "USD") == ("USD", "US Dollar", 2, "€")

    def test_max_length_is_accepted(self, db: sqlite3.Connection) -> None:
        add_currency(db, name="x" * 100)
        assert fetch_currency(db, "EUR") == ("EUR", "x" * 100, 2, "€")

    def test_over_max_length_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_currency(db, name="x" * 101)


class TestMinorUnit:
    """Tests of the `currencies.minor_unit` column."""

    @pytest.mark.parametrize("minor_unit", [
        pytest.param(0, id="lower_bound"),
        pytest.param(4, id="upper_bound"),
        pytest.param(2, id="typical"),
    ])
    def test_valid_is_accepted(self, db: sqlite3.Connection, minor_unit: int) -> None:
        add_currency(db, minor_unit=minor_unit)
        assert fetch_currency(db, "EUR") == ("EUR", "Euro", minor_unit, "€")

    @pytest.mark.parametrize("minor_unit", [
        pytest.param(-1,    id="below_lower_bound"),
        pytest.param(5,     id="above_upper_bound"),
        pytest.param(1.5,   id="fraction"),
        pytest.param(None,  id="null"),
        pytest.param("two", id="text"),
    ])
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, minor_unit: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="minor_unit"):
            add_currency(db, minor_unit=minor_unit)

    @pytest.mark.parametrize("minor_unit", [
        pytest.param(2.0, id="real"),
        pytest.param("2", id="text"),
    ])
    def test_lossless_value_is_stored_as_integer(
        self, db: sqlite3.Connection, minor_unit: object
    ) -> None:
        # STRICT converts values that fit exactly, so these become INTEGER 2.
        add_currency(db, minor_unit=minor_unit)
        row = db.execute(
            "SELECT minor_unit, typeof(minor_unit) FROM currencies"
        ).fetchone()
        assert row == (2, "integer")


class TestSymbol:
    """Tests of the `currencies.symbol` column."""

    def test_is_optional(self, db: sqlite3.Connection) -> None:
        add_currency(db, symbol=None)
        assert fetch_currency(db, "EUR") == ("EUR", "Euro", 2, None)

    @pytest.mark.parametrize("symbol", [
        pytest.param("", id="empty"),
        *WHITESPACE,
    ])
    def test_blank_is_rejected(self, db: sqlite3.Connection, symbol: str) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="symbol"):
            add_currency(db, symbol=symbol)

    @pytest.mark.parametrize("whitespace", WHITESPACE)
    @pytest.mark.parametrize("template", PADDING)
    def test_surrounding_whitespace_is_rejected(
        self, db: sqlite3.Connection, template: str, whitespace: str
    ) -> None:
        symbol = template.format(whitespace=whitespace, value="€")
        with pytest.raises(sqlite3.IntegrityError, match="symbol"):
            add_currency(db, symbol=symbol)

    def test_max_length_is_accepted(self, db: sqlite3.Connection) -> None:
        add_currency(db, symbol="x" * 16)
        assert fetch_currency(db, "EUR") == ("EUR", "Euro", 2, "x" * 16)

    def test_over_max_length_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="symbol"):
            add_currency(db, symbol="x" * 17)
