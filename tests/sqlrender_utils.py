"""Shared test utilities for SqlRender translation parity tests."""

import re


def normalize_sql(sql: str) -> str:
    """Normalize SQL whitespace for comparison.

    Matches the R test suite's `expect_equal_ignore_spaces` function exactly:
    gsub("([;()'+-/|*\n])", " \\1 ", string)

    Note: In R, `[+-/]` is a character range from ASCII 43 to 47 that includes:
    + (43), , (44), - (45), . (46), / (47).
    """
    sql = re.sub(r"([;()'+,.\-/*|\n])", r" \1 ", sql)
    sql = re.sub(r" +", " ", sql)
    return sql.strip()


def assert_sql_equal(actual: str, expected: str) -> None:
    """Assert two SQL strings are equal after whitespace normalization."""
    assert normalize_sql(actual) == normalize_sql(expected), (
        f"\nExpected: {expected}\nActual:   {actual}\n"
        f"Norm exp: {normalize_sql(expected)}\n"
        f"Norm act: {normalize_sql(actual)}"
    )
