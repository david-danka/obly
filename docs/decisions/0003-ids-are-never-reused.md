# 3. Ids are never reused

- Status: Accepted
- Date: 2026-10-19

## Context

A SQLite `INTEGER PRIMARY KEY` gives each new row the largest existing id
plus one. If the row with the highest id is deleted, the next new row gets
that same id.

Ids leave the database: in exports and CSV files, in backups compared with
the current state, in logs, and in commands like `obly account show 7`.
After a reuse, an old reference to "account 7" silently points to a
different account. In a finance app, that can mix up records without anyone
noticing.

## Decision

Tables whose ids can leave the database use
`INTEGER PRIMARY KEY AUTOINCREMENT`. SQLite then remembers the largest id
ever used, in its built-in `sqlite_sequence` table, and never hands it out
again.

This applies to `accounts` now, and to transactions once that table exists.
`currencies` doesn't need it, because its key is the ISO 4217 code.

## Consequences

- An id means the same record for the whole life of the database.
- Every insert also writes to `sqlite_sequence`. SQLite's documentation
  advises against `AUTOINCREMENT` unless it is needed because of that cost,
  but for a personal finance app it is too small to measure.
- `TestId::test_deleted_id_is_not_reused` in `tests/schema/test_accounts.py`
  checks it, and fails without `AUTOINCREMENT`.
