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
  They repeat the constants in src/obly/limits.py; the tests check that
  both agree.
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

-- Transactions: money into (positive amount) or out of (negative amount)
-- one account, in minor units of the account's currency. A regular
-- transaction has a category; an opening balance is the money an account
-- already held when tracking began, so it has none. Transfers between
-- accounts have their own table.
CREATE TABLE transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id   INTEGER NOT NULL
                 REFERENCES accounts (id) ON DELETE RESTRICT,
    kind         TEXT NOT NULL
                 DEFAULT 'regular'
                 CHECK (kind IN ('regular', 'opening_balance')),
    category_id  INTEGER
                 REFERENCES categories (id) ON DELETE RESTRICT,
    occurred_on  TEXT NOT NULL
                 CHECK (date(occurred_on) IS occurred_on),
    amount       INTEGER NOT NULL
                 CHECK (amount <> 0),
    note         TEXT
                 CHECK (
                     note <> ''
                     AND note = trim(note, char(9, 10, 13, 32, 160))
                     AND length(note) <= 500
                 ),
    created_at   TEXT NOT NULL
                 DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                 CHECK (
                     strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS created_at
                 ),
    CHECK (
        (kind = 'regular' AND category_id IS NOT NULL)
        OR (kind = 'opening_balance' AND category_id IS NULL)
    )
) STRICT;

-- An account has at most one opening balance; without one, it started empty.
CREATE UNIQUE INDEX uq_transactions_opening_balance_account_id
    ON transactions (account_id)
    WHERE kind = 'opening_balance';

CREATE INDEX idx_transactions_account_id_occurred_on
    ON transactions (account_id, occurred_on);
CREATE INDEX idx_transactions_category_id_occurred_on
    ON transactions (category_id, occurred_on);
CREATE INDEX idx_transactions_occurred_on
    ON transactions (occurred_on);

-- An opening balance is where an account's history starts, so no other
-- transaction of the account may be dated before it. Same day is fine.
CREATE TRIGGER trg_transactions_opening_balance_first_on_insert
BEFORE INSERT ON transactions
WHEN
    (
        NEW.kind = 'opening_balance'
        AND (
            EXISTS (
                SELECT 1 FROM transactions
                WHERE account_id = NEW.account_id
                    AND occurred_on < NEW.occurred_on
            )
            OR EXISTS (
                SELECT 1 FROM transfers
                WHERE NEW.account_id
                        IN (from_account_id, to_account_id)
                    AND occurred_on < NEW.occurred_on
            )
        )
    )
    OR (
        NEW.kind = 'regular'
        AND EXISTS (
            SELECT 1 FROM transactions
            WHERE account_id = NEW.account_id
                AND kind = 'opening_balance'
                AND occurred_on > NEW.occurred_on
        )
    )
BEGIN
    SELECT RAISE(
        ABORT,
        'an opening balance must be the earliest transaction of its account'
    );
END;

CREATE TRIGGER trg_transactions_opening_balance_first_on_update
BEFORE UPDATE OF account_id, kind, occurred_on ON transactions
WHEN
    (
        NEW.kind = 'opening_balance'
        AND (
            EXISTS (
                SELECT 1 FROM transactions
                WHERE account_id = NEW.account_id
                    AND id <> NEW.id
                    AND occurred_on < NEW.occurred_on
            )
            OR EXISTS (
                SELECT 1 FROM transfers
                WHERE NEW.account_id
                        IN (from_account_id, to_account_id)
                    AND occurred_on < NEW.occurred_on
            )
        )
    )
    OR (
        NEW.kind = 'regular'
        AND EXISTS (
            SELECT 1 FROM transactions
            WHERE account_id = NEW.account_id
                AND id <> NEW.id
                AND kind = 'opening_balance'
                AND occurred_on > NEW.occurred_on
        )
    )
BEGIN
    SELECT RAISE(
        ABORT,
        'an opening balance must be the earliest transaction of its account'
    );
END;

/*
Transfers: money moving between two of your own accounts. Amounts are
positive, in minor units of each account's currency; the money leaves
from_account_id and arrives in to_account_id. The two amounts can only
differ between accounts with different currencies.
*/
CREATE TABLE transfers (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    from_account_id  INTEGER NOT NULL
                     REFERENCES accounts (id) ON DELETE RESTRICT,
    to_account_id    INTEGER NOT NULL
                     REFERENCES accounts (id) ON DELETE RESTRICT,
    occurred_on      TEXT NOT NULL
                     CHECK (date(occurred_on) IS occurred_on),
    from_amount      INTEGER NOT NULL
                     CHECK (from_amount > 0),
    to_amount        INTEGER NOT NULL
                     CHECK (to_amount > 0),
    note             TEXT
                     CHECK (
                         note <> ''
                         AND note = trim(note, char(9, 10, 13, 32, 160))
                         AND length(note) <= 500
                     ),
    created_at       TEXT NOT NULL
                     DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                     CHECK (
                         strftime('%Y-%m-%dT%H:%M:%fZ', created_at)
                         IS created_at
                     ),
    CHECK (from_account_id <> to_account_id)
) STRICT;

CREATE INDEX idx_transfers_from_account_id_occurred_on
    ON transfers (from_account_id, occurred_on);
CREATE INDEX idx_transfers_to_account_id_occurred_on
    ON transfers (to_account_id, occurred_on);
CREATE INDEX idx_transfers_occurred_on
    ON transfers (occurred_on);

-- Between accounts of the same currency, what leaves must arrive.
CREATE TRIGGER trg_transfers_same_currency_amounts_on_insert
BEFORE INSERT ON transfers
WHEN
    NEW.from_amount <> NEW.to_amount
    AND (SELECT currency_code FROM accounts WHERE id = NEW.from_account_id)
        = (SELECT currency_code FROM accounts WHERE id = NEW.to_account_id)
BEGIN
    SELECT RAISE(
        ABORT,
        'a transfer within one currency must move equal amounts'
    );
END;

CREATE TRIGGER trg_transfers_same_currency_amounts_on_update
BEFORE UPDATE OF from_account_id, to_account_id, from_amount, to_amount
    ON transfers
WHEN
    NEW.from_amount <> NEW.to_amount
    AND (SELECT currency_code FROM accounts WHERE id = NEW.from_account_id)
        = (SELECT currency_code FROM accounts WHERE id = NEW.to_account_id)
BEGIN
    SELECT RAISE(
        ABORT,
        'a transfer within one currency must move equal amounts'
    );
END;

-- A transfer can't be dated before the opening balance of either account.
CREATE TRIGGER trg_transfers_opening_balance_first_on_insert
BEFORE INSERT ON transfers
WHEN
    EXISTS (
        SELECT 1 FROM transactions
        WHERE account_id IN (NEW.from_account_id, NEW.to_account_id)
            AND kind = 'opening_balance'
            AND occurred_on > NEW.occurred_on
    )
BEGIN
    SELECT RAISE(
        ABORT,
        'an opening balance must be the earliest transaction of its account'
    );
END;

CREATE TRIGGER trg_transfers_opening_balance_first_on_update
BEFORE UPDATE OF from_account_id, to_account_id, occurred_on ON transfers
WHEN
    EXISTS (
        SELECT 1 FROM transactions
        WHERE account_id IN (NEW.from_account_id, NEW.to_account_id)
            AND kind = 'opening_balance'
            AND occurred_on > NEW.occurred_on
    )
BEGIN
    SELECT RAISE(
        ABORT,
        'an opening balance must be the earliest transaction of its account'
    );
END;

COMMIT;
