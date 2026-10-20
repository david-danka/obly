/*
obly: database schema

Tables and constraints only; no seed data.
Foreign keys are enabled per connection by the app, not here.

Conventions used in checks:
- The schema enforces the shape of values; which values exist and what
  they mean is up to the app.
- Identifiers (code, kind) are ASCII with a strict format; display text
  (name, symbol) may be any Unicode.
- Whitespace set: tab, LF, CR, space, NBSP, i.e. char(9, 10, 13, 32, 160).
- Text length limits only keep garbage out; they are not business rules.
- Ids that can leave the database are never reused (AUTOINCREMENT).

The reasoning behind these is in docs/decisions/.
*/

BEGIN;

PRAGMA user_version = 1;

-- Currencies (ISO 4217)
CREATE TABLE currencies (
    code        TEXT NOT NULL PRIMARY KEY
                CHECK (code GLOB '[A-Z][A-Z][A-Z]'),
    name        TEXT NOT NULL
                CHECK (
                    name <> ''
                    AND name = trim(name, char(9, 10, 13, 32, 160))
                    AND length(name) <= 100
                ),
    minor_unit  INTEGER NOT NULL
                CHECK (minor_unit BETWEEN 0 AND 4),
    symbol      TEXT
                CHECK (
                    symbol <> ''
                    AND symbol = trim(symbol, char(9, 10, 13, 32, 160))
                    AND length(symbol) <= 16
                )
) STRICT, WITHOUT ROWID;

/*
Accounts: where the money is
kind is a lowercase identifier such as cash or credit_card. Which kinds
exist and what they mean is defined in the app, not here.
*/
CREATE TABLE accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE COLLATE NOCASE
                    CHECK (
                        name <> ''
                        AND name = trim(name, char(9, 10, 13, 32, 160))
                        AND length(name) <= 100
                    ),
    kind            TEXT NOT NULL
                    CHECK (
                        kind GLOB '[a-z]*'
                        AND kind NOT GLOB '*[^a-z_]*'
                        AND length(kind) <= 50
                    ),
    currency_code   TEXT NOT NULL
                    REFERENCES currencies (code) ON DELETE RESTRICT,
    is_archived     INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (is_archived IN (0, 1)),
    created_at      TEXT NOT NULL
                    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                    CHECK (strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS created_at)
) STRICT;

CREATE INDEX idx_accounts_currency_code ON accounts (currency_code);

/*
Categories: what money is spent on or earned from, nested at most two
levels deep (category and subcategory).
kind is a fixed list: income vs expense is a fact of bookkeeping, not a 
policy that may change.
*/
CREATE TABLE categories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id    INTEGER,
    name         TEXT NOT NULL COLLATE NOCASE
                 CHECK (
                     name <> ''
                     AND name = trim(name, char(9, 10, 13, 32, 160))
                     AND length(name) <= 100
                 ),
    kind         TEXT NOT NULL
                 CHECK (kind IN ('income', 'expense')),
    is_archived  INTEGER NOT NULL
                 DEFAULT 0
                 CHECK (is_archived IN (0, 1)),
    CHECK (parent_id IS NULL OR parent_id <> id),
    -- A subcategory has the same kind as its parent.
    UNIQUE (id, kind),
    FOREIGN KEY (parent_id, kind)
        REFERENCES categories (id, kind) ON DELETE RESTRICT
) STRICT;

CREATE UNIQUE INDEX uq_categories_top_level_name_kind
    ON categories (name, kind)
    WHERE parent_id IS NULL;
CREATE UNIQUE INDEX uq_categories_parent_name
    ON categories (parent_id, name)
    WHERE parent_id IS NOT NULL;

-- Keep the tree two levels deep, which also rules out cycles.
CREATE TRIGGER trg_categories_depth_on_insert
BEFORE INSERT ON categories
WHEN
    NEW.parent_id IS NOT NULL
    AND (SELECT parent_id FROM categories WHERE id = NEW.parent_id)
        IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'categories nest at most two levels deep');
END;

CREATE TRIGGER trg_categories_depth_on_update
BEFORE UPDATE OF parent_id ON categories
WHEN
    NEW.parent_id IS NOT NULL
    AND (
        (SELECT parent_id FROM categories WHERE id = NEW.parent_id)
            IS NOT NULL
        OR EXISTS (SELECT 1 FROM categories WHERE parent_id = NEW.id)
    )
BEGIN
    SELECT RAISE(ABORT, 'categories nest at most two levels deep');
END;

COMMIT;
