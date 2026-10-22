# To-do

Concrete tasks, as opposed to the product features in the
[roadmap](roadmap.md). Delete an item once it's done; git history keeps
the record.

## For the MVP

- [ ] **Schema migrations:** numbered upgrade steps, applied at startup
      based on `PRAGMA user_version`. Needed before entering real data, so
      later schema changes don't mean starting over.
- [ ] **Repositories and services** for accounts, categories,
      transactions and transfers, under the CLI.
- [ ] **Signs from categories:** derive an amount's sign from its
      category's kind, with an explicit refund action that flips it.
- [ ] **User text:** normalize to NFC, strip whitespace, and check names
      for duplicates with `str.casefold()` (decision 2).
- [ ] **Account kinds** as an `Enum` with display names, starting from the
      candidates in decision 1.

## After the MVP

### Schema

- [ ] **Category depth:** let the schema rule out only cycles, and enforce
      the two-level limit in the app (decision 1: the depth is a policy).
- [ ] **SQL style pass:** write the SQL style rules into the `schema.sql`
      header and make the whole file follow them.
- [ ] **Decision record 6:** why transfers have their own table.

### App

- [ ] **Changing a category's kind** asks for confirmation, since it
      reclassifies past transactions.

### Testing and tooling

- [ ] **Property-based tests** with Hypothesis at the service layer:
      money conversion, recurring dates, projections, and stateful tests of
      the services against a simple model.
- [ ] **Mutation testing** with `mutmut`, run now and then, once there's
      real Python logic.
- [ ] **Trailing commas:** one parameter per line for multi-line
      signatures, project-wide.
- [ ] **`mypy_path = "tests"`** under `[tool.mypy]`, so the editor's mypy
      finds `text_cases`.

### Docs

- [ ] **README:** the story behind the name, and links to the docs.
- [ ] **Working agreements** for the project.

## Ideas, not yet scheduled

- [ ] **Payments abroad by card:** keep the original amount and currency.
- [ ] **Refund link:** an optional reference from a refund to its purchase.
- [ ] **Recurring transactions and transfers,** for installments and
      sinking funds.
- [ ] **Loan repayment schedules,** to split installments into principal
      and interest from the loan's rate.
