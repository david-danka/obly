# 1. The schema enforces shape, the app enforces meaning

- Status: Accepted
- Date: 2026-10-19

## Context

SQLite CHECK constraints can enforce two different kinds of rules:

- **Shape:** what makes a value malformed, no matter who writes it. For
  example a blank name, a currency code that isn't three uppercase letters,
  or a reference to a currency that doesn't exist.
- **Meaning:** which values the app supports and how it treats them. For
  example which kinds of accounts exist.

`accounts.kind` forced the question. The app will branch on it, so its
values matter, but the list of kinds isn't settled yet. Enforcing the list
with `CHECK (kind IN (...))` would put it in two places, because the code
that branches on the kind needs the list too. Every change would then mean
updating both and writing a schema migration.

## Decision

A rule goes into the schema if breaking it makes the data wrong whoever
wrote it: `NOT NULL`, formats, trimmed text, length limits, uniqueness and
foreign keys.

A rule stays in the app if it is a policy that can reasonably change: which
values exist and what they mean.

Facts from outside standards count as shape. `currencies.minor_unit` stays
limited to 0 to 4 in the schema, because ISO 4217 defines that range.

## Consequences

- `accounts.kind` only has to be a lowercase identifier in the schema. The
  app defines the set of kinds, most likely as a Python `Enum`, which is the
  single source of truth for the code that branches on it.
- Changing the set of kinds needs no schema migration.
- Anything that writes to the database without going through obly, such as
  editing the file in DB Browser for SQLite, can store a kind the app
  doesn't know. The app must refuse such a value with a clear error when it
  reads it, instead of guessing.
- The tests document the split: the schema accepts `crypto`, a well-formed
  kind the app doesn't define.

The first candidate kinds, for the future `Enum`:

| Kind          | Meaning                                         |
|---------------|-------------------------------------------------|
| `cash`        | wallet, physical money                          |
| `checking`    | everyday bank account                           |
| `savings`     | savings account, deposits                       |
| `credit_card` | card with a balance you owe                     |
| `brokerage`   | holds securities you trade (stocks, bonds, ETFs) |
| `pension`     | retirement fund, valued from statements         |
| `loan`        | mortgage, car loan, personal loan               |
