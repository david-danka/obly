# 2. Identifiers are ASCII, display text is Unicode

- Status: Accepted
- Date: 2026-10-19

## Context

The schema has two kinds of text columns:

- **Identifiers** that the program compares against: `currencies.code` and
  `accounts.type`.
- **Display text** that people type and read: `currencies.name`,
  `currencies.symbol` and `accounts.name`.

Unicode text has pitfalls that matter for both:

- The same visible text can be stored in different ways. `á` can be one
  character or `a` followed by a combining accent; the two look identical
  but compare as different.
- SQLite's `COLLATE NOCASE` only ignores case for ASCII letters, so
  `Számla` and `SZÁMLA` count as different names.
- SQLite's `trim()` only strips the characters it is given.

## Decision

Identifiers are ASCII with a strict format:

- `currencies.code`: three uppercase letters, as in ISO 4217.
- `accounts.type`: lowercase letters and underscores, starting with a
  letter, at most 50 characters.

What users see for an identifier, such as "Hitelkártya" for
`credit_card`, is a display name the app provides, so the stored value
doesn't depend on the interface language.

Display text may contain any Unicode. The schema only checks its shape: not
blank, no surrounding whitespace and a length limit (100 characters for
names, 16 for symbols). The whitespace set is tab, LF, CR, space and NBSP,
the characters that actually show up in typed or pasted text.

## Consequences

- Comparisons on identifiers are always reliable, and identifiers work as
  they are in code, command-line arguments, exports and config files.
- Before saving user text, the app must:
  1. normalize it with `unicodedata.normalize("NFC", text)`, so every
     character is stored in one form;
  2. strip surrounding whitespace with `str.strip()`, which knows all
     Unicode whitespace, not just the five characters the schema checks;
  3. check for duplicates with `str.casefold()`, which covers the case gap
     `COLLATE NOCASE` leaves for non-ASCII letters.
- The database checks stay a backstop for the common cases. The test
  `TestName::test_non_ascii_case_variant_is_accepted` in
  `tests/schema/test_accounts.py` documents the `NOCASE` gap.
