"""Shared test cases for the schema's text checks.

Use them with `pytest.mark.parametrize` in tests of columns that must not
be blank and must not have surrounding whitespace.
"""

import pytest

# The whitespace set the schema's checks strip: tab, LF, CR, space, NBSP.
WHITESPACE = [
    pytest.param("\t", id="tab"),
    pytest.param("\n", id="lf"),
    pytest.param("\r", id="cr"),
    pytest.param(" ", id="space"),
    pytest.param("\u00a0", id="nbsp"),
]

# Templates that put a whitespace character before or after a value.
PADDING = [
    pytest.param("{whitespace}{value}", id="leading"),
    pytest.param("{value}{whitespace}", id="trailing"),
]
