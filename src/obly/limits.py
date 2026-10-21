"""Maximum lengths of text values, shared by the app and the schema.

schema.sql can't import Python, so its CHECK constraints repeat these
numbers. The schema tests use these constants, so they fail if the two
ever disagree. The limits only keep garbage out; they are not business
rules.
"""

# Names of currencies, accounts and categories.
NAME_MAX_LENGTH = 100

# Currency symbols, such as "Ft" or "€".
SYMBOL_MAX_LENGTH = 16

# Account kinds, identifiers such as "credit_card".
ACCOUNT_KIND_MAX_LENGTH = 50

# Notes on transactions.
NOTE_MAX_LENGTH = 500
