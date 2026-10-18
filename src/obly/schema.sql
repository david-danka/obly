/*
obly: database schema

Tables and constraints only; no seed data.
Foreign keys are enabled per connection by the app, not here.

Conventions used in checks:
- Whitespace set: tab, LF, CR, space, NBSP, i.e. char(9, 10, 13, 32, 160).
- Text length limits only keep garbage out; they are not business rules.
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

COMMIT;
