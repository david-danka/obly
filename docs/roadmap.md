# Roadmap

Tiers are built in order. Each tier lands as new tables and modules, never
as rewrites of earlier ones (see the [vision](vision.md)).

✅ done · ⬜ to do

## 1. MVP: where did my money go?

The smallest obly you can use with real money.

- ✅ **Currencies:** ISO 4217 codes and their minor units.
- ✅ **Accounts:** where money is kept, each in one currency.
- ✅ **Categories:** income or expense, with optional subcategories.
- ✅ **Transactions:** signed amounts, opening balances, refunds.
- ✅ **Transfers:** between your own accounts, also across currencies.
- ✅ **Balances:** an `account_entries` view that combines transactions and
  transfers, so a balance is a single sum.
- ✅ **Currency freeze:** an account's currency can't change once money is
  recorded on it, or every stored amount would change meaning.
- ⬜ **CLI:** add, list, edit and delete transactions and transfers; show
  balances; show spending by category per month.

## 1b. MVP+: planning the month

- ⬜ **Base currency:** the currency budgets and totals are reported in.
- ⬜ **Budgets:** planned monthly spending per expense category, in the base
  currency. Budgets and spending reports ignore investment and pension
  accounts.
- ⬜ **Earmarks:** money set aside for a purpose, such as replacing a fridge,
  while it stays in the same bank account. An account then shows its
  balance, what's reserved, and what's available.
- ⬜ **CSV export.** No import yet.

## 2. Net worth

- ⬜ **Valuations:** manual snapshots, such as pension fund statements.
- ⬜ **Exchange rates by date,** for totals across currencies.
- ⬜ **Net worth over time,** contributions vs value, and return (IRR).
- ⬜ **Property and depreciation:** asset accounts for big things you own,
  such as a car or a flat. Buying one is a transfer, not an expense, and a
  monthly depreciation transaction lowers its value over its useful life.

## 3. Investments

- ⬜ **Instruments:** stocks, bonds, ETFs and funds.
- ⬜ **Trades:** buy and sell, with units, price and fees.
- ⬜ **Price history.**
- ⬜ **Cost basis,** and realized and unrealized gains. Dividends and coupons
  are ordinary income transactions.

## 4. Lifetime planner

- ⬜ **Goals,** each funded by one or more accounts.
- ⬜ **A profile:** birth date, retirement age, and inflation and return
  assumptions.
- ⬜ **Projections and scenarios,** later Monte Carlo simulations.

## 5. Machine learning

- ⬜ **Auto-categorization** of transactions.
- ⬜ **Spending forecasts.**

## 6. GUI

- ⬜ **PySide6,** on top of the same services as the CLI. The order is
  flexible, since the CLI and the GUI share all logic.
