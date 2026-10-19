/*
obly: database schema

Tables and constraints only; no seed data.
Foreign keys are enabled per connection by the app, not here.

Conventions used in checks:
- The schema enforces the shape of values; which values exist and what
  they mean is up to the app.
- Identifiers (code, type) are ASCII with a strict format; display text
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
type is a lowercase identifier such as cash or credit_card. Which types
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
    type            TEXT NOT NULL
                    CHECK (
                        type GLOB '[a-z]*'
                        AND type NOT GLOB '*[^a-z_]*'
                        AND length(type) <= 50
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

CREATE INDEX accounts_currency_code ON accounts (currency_code);

COMMIT;
