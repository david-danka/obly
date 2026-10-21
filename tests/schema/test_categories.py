"""Tests of the `categories` table."""

import sqlite3

import pytest

from obly.limits import NAME_MAX_LENGTH
from text_cases import PADDING, WHITESPACE


def add_category(
    db: sqlite3.Connection,
    name: object = "Food",
    kind: object = "expense",
    parent_id: object = None,
    **columns: object,
) -> int:
    """Insert one row into `categories`.

    Every named argument has a valid sample value, so a test only passes
    the one it wants to break; by default the category is top-level.
    Columns not passed at all, such as `is_archived`, get the table's
    `DEFAULT`s. The values are typed `object` because tests pass
    deliberately invalid types.

    Args:
        db: Connection with the schema applied.
        name: Value for the `name` column.
        kind: Value for the `kind` column.
        parent_id: Value for the `parent_id` column.
        **columns: Values for any other columns, by column name.

    Returns:
        The `id` of the new row.
    """
    values = {
        "name": name,
        "kind": kind,
        "parent_id": parent_id,
        **columns,
    }
    names = ", ".join(values)
    placeholders = ", ".join("?" * len(values))
    cursor = db.execute(
        f"INSERT INTO categories ({names}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def fetch_column(
    db: sqlite3.Connection, category_id: int, column: str
) -> object:
    """Fetch one column of one row from `categories`.

    Args:
        db: Connection with the schema applied.
        category_id: The `id` of the row.
        column: The name of the column.

    Returns:
        The column's value.
    """
    return db.execute(
        f"SELECT {column} FROM categories WHERE id = ?", (category_id,)
    ).fetchone()[0]


def set_parent(
    db: sqlite3.Connection, category_id: int, parent_id: int | None
) -> None:
    """Move a category under another one, or make it top-level.

    Args:
        db: Connection with the schema applied.
        category_id: The `id` of the category to move.
        parent_id: The `id` of the new parent, or None for top-level.
    """
    db.execute(
        "UPDATE categories SET parent_id = ? WHERE id = ?",
        (parent_id, category_id),
    )


def test_valid_category_is_stored(db: sqlite3.Connection) -> None:
    category_id = add_category(db)
    row = db.execute(
        """
        SELECT name, kind, parent_id, is_archived
        FROM categories
        WHERE id = ?
        """,
        (category_id,),
    ).fetchone()
    assert row == ("Food", "expense", None, 0)


class TestId:
    """Tests of the `categories.id` column."""

    def test_deleted_id_is_not_reused(self, db: sqlite3.Connection) -> None:
        add_category(db, name="Food")
        deleted_id = add_category(db, name="Transport")
        db.execute("DELETE FROM categories WHERE id = ?", (deleted_id,))
        new_id = add_category(db, name="Housing")
        assert new_id > deleted_id


class TestName:
    """Tests of the `categories.name` column."""

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
            add_category(db, name=name)

    @pytest.mark.parametrize("whitespace", WHITESPACE)
    @pytest.mark.parametrize("template", PADDING)
    def test_surrounding_whitespace_is_rejected(
        self, db: sqlite3.Connection, template: str, whitespace: str
    ) -> None:
        name = template.format(whitespace=whitespace, value="Food")
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_category(db, name=name)

    def test_inner_whitespace_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        category_id = add_category(db, name="Eating Out")
        assert fetch_column(db, category_id, "name") == "Eating Out"

    def test_max_length_is_accepted(self, db: sqlite3.Connection) -> None:
        category_id = add_category(db, name="x" * NAME_MAX_LENGTH)
        assert fetch_column(db, category_id, "name") == "x" * NAME_MAX_LENGTH

    def test_over_max_length_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="name"):
            add_category(db, name="x" * (NAME_MAX_LENGTH + 1))


class TestKind:
    """Tests of the `categories.kind` column."""

    @pytest.mark.parametrize("kind", ["income", "expense"])
    def test_known_kind_is_accepted(
        self, db: sqlite3.Connection, kind: str
    ) -> None:
        category_id = add_category(db, kind=kind)
        assert fetch_column(db, category_id, "kind") == kind

    @pytest.mark.parametrize(
        "kind",
        [
            pytest.param("transfer", id="unknown"),
            pytest.param("Income", id="wrong_case"),
            pytest.param(" income", id="surrounding_whitespace"),
            pytest.param("", id="empty"),
            pytest.param(None, id="null"),
        ],
    )
    def test_invalid_is_rejected(
        self, db: sqlite3.Connection, kind: object
    ) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="kind"):
            add_category(db, kind=kind)

    def test_subcategory_of_other_kind_is_rejected(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food", kind="expense")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            add_category(db, name="Salary", kind="income", parent_id=food)

    def test_subcategory_cannot_move_under_other_kind(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food", kind="expense")
        salary = add_category(db, name="Salary", kind="income")
        bonus = add_category(db, name="Bonus", kind="income", parent_id=salary)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            set_parent(db, bonus, food)

    def test_parent_kind_cannot_change_while_it_has_subcategories(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food", kind="expense")
        add_category(db, name="Groceries", kind="expense", parent_id=food)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute(
                "UPDATE categories SET kind = 'income' WHERE id = ?", (food,)
            )


class TestParentId:
    """Tests of the `categories.parent_id` column."""

    def test_unknown_parent_is_rejected(self, db: sqlite3.Connection) -> None:
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            add_category(db, name="Groceries", parent_id=999)

    def test_category_cannot_be_its_own_parent(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        with pytest.raises(sqlite3.IntegrityError, match="parent_id"):
            set_parent(db, food, food)

    def test_parent_with_subcategories_cannot_be_deleted(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        add_category(db, name="Groceries", parent_id=food)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute("DELETE FROM categories WHERE id = ?", (food,))

    def test_category_without_subcategories_can_be_deleted(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        db.execute("DELETE FROM categories WHERE id = ?", (food,))
        count = db.execute("SELECT count(*) FROM categories").fetchone()[0]
        assert count == 0


class TestUniqueness:
    """Tests of the unique names among top-level and sibling categories."""

    @pytest.mark.parametrize(
        "duplicate",
        [
            pytest.param("Food", id="same_case"),
            pytest.param("FOOD", id="upper_case"),
            pytest.param("food", id="lower_case"),
        ],
    )
    def test_duplicate_top_level_name_is_rejected(
        self, db: sqlite3.Connection, duplicate: str
    ) -> None:
        add_category(db, name="Food")
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            add_category(db, name=duplicate)

    def test_same_top_level_name_with_other_kind_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        add_category(db, name="Other", kind="expense")
        add_category(db, name="Other", kind="income")
        count = db.execute("SELECT count(*) FROM categories").fetchone()[0]
        assert count == 2

    @pytest.mark.parametrize(
        "duplicate",
        [
            pytest.param("Groceries", id="same_case"),
            pytest.param("GROCERIES", id="upper_case"),
        ],
    )
    def test_duplicate_sibling_name_is_rejected(
        self, db: sqlite3.Connection, duplicate: str
    ) -> None:
        food = add_category(db, name="Food")
        add_category(db, name="Groceries", parent_id=food)
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            add_category(db, name=duplicate, parent_id=food)

    def test_same_name_under_different_parents_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        transport = add_category(db, name="Transport")
        add_category(db, name="Other", parent_id=food)
        add_category(db, name="Other", parent_id=transport)
        count = db.execute(
            "SELECT count(*) FROM categories WHERE name = 'Other'"
        ).fetchone()[0]
        assert count == 2

    def test_subcategory_may_share_a_top_level_name(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        add_category(db, name="Groceries")
        add_category(db, name="Groceries", parent_id=food)
        count = db.execute(
            "SELECT count(*) FROM categories WHERE name = 'Groceries'"
        ).fetchone()[0]
        assert count == 2

    def test_non_ascii_case_variant_is_accepted(
        self, db: sqlite3.Connection
    ) -> None:
        # Known gap: COLLATE NOCASE only folds ASCII letters, so the app
        # must catch duplicates like these with str.casefold().
        add_category(db, name="Élelmiszer")
        add_category(db, name="élelmiszer")
        count = db.execute("SELECT count(*) FROM categories").fetchone()[0]
        assert count == 2


class TestDepth:
    """Tests of the two-level limit, which also rules out cycles."""

    def test_grandchild_is_rejected(self, db: sqlite3.Connection) -> None:
        food = add_category(db, name="Food")
        groceries = add_category(db, name="Groceries", parent_id=food)
        with pytest.raises(sqlite3.IntegrityError, match="two levels"):
            add_category(db, name="Organic", parent_id=groceries)

    def test_category_cannot_move_under_a_subcategory(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        groceries = add_category(db, name="Groceries", parent_id=food)
        transport = add_category(db, name="Transport")
        with pytest.raises(sqlite3.IntegrityError, match="two levels"):
            set_parent(db, transport, groceries)

    def test_category_with_subcategories_cannot_get_a_parent(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        add_category(db, name="Groceries", parent_id=food)
        housing = add_category(db, name="Housing")
        with pytest.raises(sqlite3.IntegrityError, match="two levels"):
            set_parent(db, food, housing)

    def test_cycle_is_rejected(self, db: sqlite3.Connection) -> None:
        food = add_category(db, name="Food")
        groceries = add_category(db, name="Groceries", parent_id=food)
        with pytest.raises(sqlite3.IntegrityError, match="two levels"):
            set_parent(db, food, groceries)

    def test_subcategory_can_move_to_another_parent(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        housing = add_category(db, name="Housing")
        utilities = add_category(db, name="Utilities", parent_id=food)
        set_parent(db, utilities, housing)
        assert fetch_column(db, utilities, "parent_id") == housing

    def test_subcategory_can_become_top_level(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        groceries = add_category(db, name="Groceries", parent_id=food)
        set_parent(db, groceries, None)
        assert fetch_column(db, groceries, "parent_id") is None

    def test_top_level_category_can_become_a_subcategory(
        self, db: sqlite3.Connection
    ) -> None:
        food = add_category(db, name="Food")
        groceries = add_category(db, name="Groceries")
        set_parent(db, groceries, food)
        assert fetch_column(db, groceries, "parent_id") == food


class TestIsArchived:
    """Tests of the `categories.is_archived` column."""

    def test_defaults_to_not_archived(self, db: sqlite3.Connection) -> None:
        category_id = add_category(db)
        assert fetch_column(db, category_id, "is_archived") == 0

    @pytest.mark.parametrize("is_archived", [0, 1])
    def test_valid_is_accepted(
        self, db: sqlite3.Connection, is_archived: int
    ) -> None:
        category_id = add_category(db, is_archived=is_archived)
        assert fetch_column(db, category_id, "is_archived") == is_archived

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
            add_category(db, is_archived=is_archived)
