"""Test replacementPatterns.csv format - ported from OHDSI SqlRender test-replacement-patterns-file-format.R"""

import pytest

from circe.sqlrender import translate
from circe.sqlrender.patterns import _safe_split


class TestCsvFormat:

    def test_csv_has_valid_format(self):
        from importlib.resources import files

        f = files("circe.sqlrender").joinpath("replacementPatterns.csv").open("r", encoding="utf-8")
        content = f.read()

        lines = content.splitlines()
        assert len(lines) > 1, "CSV should have header row plus at least one pattern"

        for i, line in enumerate(lines):
            columns = _safe_split(line, ",")
            if i == 0:
                assert columns[0] == "To"
                assert columns[1] == "Pattern"
                assert columns[2] == "Replacement"
                continue
            assert len(columns) >= 3, (
                f"Row {i} has {len(columns)} columns (expected at least 3): {columns}"
            )

    def test_all_patterns_can_be_parsed(self):
        from circe.sqlrender.translator import parse_search_pattern
        from circe.sqlrender.patterns import load_patterns

        patterns = load_patterns()
        for dialect, pairs in patterns.items():
            for pattern, replacement in pairs:
                try:
                    parse_search_pattern(pattern)
                except Exception as e:
                    pytest.fail(
                        f"Failed to parse pattern for dialect '{dialect}': "
                        f"pattern={pattern!r}, error={e}"
                    )

    def test_duckdb_and_postgresql_can_translate_simple_sql(self):
        sql = "SELECT * FROM table;"
        for dialect in ("duckdb", "postgresql"):
            result = translate(sql, dialect)
            assert "SELECT" in result
            assert "table" in result
