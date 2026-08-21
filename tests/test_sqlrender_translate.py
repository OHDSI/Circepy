"""Test general translation behavior - ported from OHDSI SqlRender test-translateSql.R"""

import pytest

from circe.sqlrender import translate
from circe.sqlrender.translator import SqlTranslateError, check


class TestGeneralTranslate:
    def test_invalid_target_dialect(self):
        with pytest.raises(SqlTranslateError, match="Don't know how to translate to"):
            translate("SELECT * FROM a;", target_dialect="pwd")

    def test_table_name_too_long_warning(self):
        warnings = check(
            "DROP TABLE abcdefghijklmnopqrstuvwxyz1234567890123456789012345678901234567890",
            "pdw",
        )
        assert len(warnings) > 0
        assert "too long" in warnings[0].lower()

    def test_no_warning_for_short_table_name(self):
        warnings = check("DROP TABLE short_name;", "pdw")
        assert len(warnings) == 0

    def test_list_supported_dialects(self):
        from circe.sqlrender.patterns import load_patterns

        patterns = load_patterns()
        for d in ("duckdb", "postgresql", "oracle", "bigquery"):
            assert d in patterns, f"Missing dialect: {d}"
