"""Test DuckDB translation - ported from OHDSI SqlRender test-translate-duckdb.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestDuckDBTranslation:
    def test_string_concat_1(self):
        sql = translate("'x' + b ( 'x' + b)", "duckdb")
        assert_sql_equal(sql, "'x' || b ( 'x' || b)")

    def test_string_concat_2(self):
        sql = translate("a + ';b'", "duckdb")
        assert_sql_equal(sql, "a || ';b'")

    def test_string_concat_3(self):
        sql = translate("a + ';('", "duckdb")
        assert_sql_equal(sql, "a || ';('")

    def test_add_months(self):
        sql = translate("DATEADD(mm,2,date)", "duckdb")
        assert_sql_equal(sql, "(date + TO_MONTHS(CAST(2 AS INTEGER)))")

    def test_add_years(self):
        sql = translate("DATEADD(yy,2,date)", "duckdb")
        assert_sql_equal(sql, "(date + TO_YEARS(CAST(2 AS INTEGER)))")

    def test_cte_select_into(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "duckdb",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE d\nAS\nWITH cte1  AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1;",
        )

    def test_select_into(self):
        sql = translate("SELECT a INTO b FROM c;", "duckdb")
        assert_sql_equal(sql, "CREATE TABLE b  AS\nSELECT\na \nFROM\nc;")

    def test_left(self):
        sql = translate("LEFT('Hello World', 5)", "duckdb")
        assert_sql_equal(sql, "LEFT('Hello World', 5)")

    def test_right(self):
        sql = translate("RIGHT('Hello World', 5)", "duckdb")
        assert_sql_equal(sql, "RIGHT('Hello World', 5)")

    def test_getdate(self):
        sql = translate("GETDATE()", "duckdb")
        assert_sql_equal(sql, "CURRENT_DATE")

    def test_stdev(self):
        sql = translate("STDEV(x)", "duckdb")
        assert_sql_equal(sql, "STDDEV(x)")

    def test_var(self):
        sql = translate("VAR(x)", "duckdb")
        assert_sql_equal(sql, "VARIANCE(x)")

    def test_square(self):
        sql = translate("SQUARE(x)", "duckdb")
        assert_sql_equal(sql, "((x) * (x))")
