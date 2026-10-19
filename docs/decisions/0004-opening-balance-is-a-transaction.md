# 4. The opening balance is a transaction

- Status: Accepted
- Date: 2026-10-19

## Context

An account usually already holds money when you start tracking it. A first
draft of the `accounts` table stored this as a `starting_balance` column,
which raised three questions it couldn't answer by itself:

- **Unit:** whole currency units or minor units (cents, fillér)?
- **Sign:** is a debt, like a credit card or a loan, negative or positive?
- **Date:** as of when? `created_at` is when the row was added, not when the
  balance was valid. You might add an account today but track it from
  January 1st.

It would also make every balance calculation a special case: the starting
balance plus the transactions.

## Decision

`accounts` has no starting balance column. An account's opening balance is
recorded as its first transaction, with its own date, as in standard
bookkeeping.

## Consequences

- Every balance is the sum of the account's transactions, with no special
  case, and every amount has a date.
- The transactions table, when it is designed, has to support opening
  balances, for example by marking them so they can be told apart from
  real income.
- The unit and the sign convention for amounts still have to be decided,
  together with the transactions table. The likely choice is minor units of
  the account's currency, which is what `currencies.minor_unit` is for.
