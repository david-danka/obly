# Vision

Every obol counts. obly is a local-first, opinionated personal finance
tracker and lifetime planner.

## What obly answers

1. **Where did my money go?**
2. **Will my money get me where I want to be?**

It covers a whole lifetime, not just next month.

## Planning horizons

1. **Monthly budget:** planned spending per category, actual vs planned.
2. **Short-term goals,** such as a vacation: cash or savings; investing
   isn't worth it.
3. **Mid-term goals,** such as a home down payment: bonds may come into
   play.
4. **Long-term goals:** retirement, financial independence, children's
   education, paying off a mortgage early.

A goal's horizon is **derived from its target date**, not stored and not
tied to an account. The thresholds (for example under 1 year short, 1 to
5 years mid, over 5 years long) are configurable.

## Core concepts

- **Accounts:** *where* the money is: cash, bank accounts, brokerage
  accounts, pension funds, and debts such as loans and credit cards. An
  account's balance is what it adds to net worth, so debts have negative
  balances ([decision 5](decisions/0005-amounts-are-signed-by-net-worth.md)).
- **Transactions:** money into or out of one account. A regular
  transaction has a category; an account's opening balance is a
  transaction of its own
  ([decision 4](decisions/0004-opening-balance-is-a-transaction.md)).
- **Transfers:** money moving between two of your own accounts, including
  between currencies. They never count as income or spending.
- **Categories:** *what* money was spent on or earned from: income or
  expense, with optional subcategories, two levels deep at most.
- **Earmarks:** money set aside for a purpose, such as replacing the
  fridge, while it stays in the same account. An account shows its
  balance, what's reserved, and what's available to spend.
- **Property:** things you own that are worth tracking, such as a car or a
  flat, valued and depreciated over their useful life.
- **Instruments:** *what* money is invested in (stocks, bonds, ETFs,
  funds), held in accounts.
- **Goals:** *what* the money is for, funded by one or more accounts.
- **Budgets** plan *flows* (monthly spending); **goals** plan *stocks* (an
  amount by a date).

## Principles

- **Local-first:** your data lives in a SQLite file on your own machine.
- **Opinionated:** every financial event has exactly one way to be
  recorded, so reports never depend on how something was entered.
- **Trustworthy data:** malformed or contradictory data can't be stored,
  whatever writes it, so every report can be trusted.
- **Additive growth:** know the whole vision, build only the current tier
  of the [roadmap](roadmap.md), and design so that the next tier adds new
  tables and modules instead of rewriting existing ones.
- **Built to learn:** obly is a personal learning project, built with
  clean, transferable skills, to do exactly what its owner wants.
