# 5. Amounts are signed by their effect on net worth

- Status: Accepted
- Date: 2026-10-20

## Context

A first draft of `transactions` stored every amount as positive and took
the direction from the category's kind. That model couldn't record:

- **Refunds:** money coming back under an expense category, such as
  returned shoes.
- **Opening balances** (decision 4): neither income nor expense.
- **Debts:** a mortgage or a credit card balance is money owed, not money
  held.

It also made every balance depend on the categories table, so changing a
category's kind would rewrite history.

## Decision

`transactions.amount` is a signed integer in minor units of the account's
currency:

- **Positive** raises the account's balance: money in, or debt paid down.
- **Negative** lowers it: money out, or debt taken on.

An account's balance is the sum of its amounts, and it says what the
account adds to net worth. Accounts that hold money have positive
balances; debts, such as a mortgage or a credit card, are accounts with
negative balances.

This gives each event exactly one way to be recorded:

| Event                        | Recorded as                                                        |
|------------------------------|--------------------------------------------------------------------|
| Groceries                    | a negative regular transaction under an expense category           |
| Salary                       | a positive regular transaction under an income category            |
| Refund                       | a positive regular transaction under the original expense category |
| Loan payout                  | a transfer from the loan account to checking                       |
| Loan installment             | a transfer from checking to the loan account                       |
| Loan interest                | a negative regular transaction on the loan account                 |
| Starting to track an account | its opening balance, negative for a debt                           |

## Consequences

- Net worth is the sum of all account balances, with no special cases for
  debts. "Money I have" and "what I owe" are the sums of the positive and
  the negative balances.
- A category's total is its net amount, so refunds reduce spending instead
  of counting as income.
- Income and expense reports only include regular transactions; opening
  balances and transfers are excluded by their kind, not by a magic
  category.
- Users never type the sign. The app derives it: from the category's kind
  by default, flipped by an explicit refund action, and typed only for an
  opening balance of a debt.
- This settles the sign convention that decision 4 left open; the unit is
  minor units, as decision 4 expected.
