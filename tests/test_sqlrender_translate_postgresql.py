"""Test PostgreSQL translation - ported from OHDSI SqlRender test-translate-postgresql.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestPostgreSQLTranslation:
    def test_use(self):
        sql = translate("USE vocabulary;", "postgresql")
        assert_sql_equal(sql, "SET search_path TO vocabulary;")

    def test_string_concat_1(self):
        sql = translate("'x' + b ( 'x' + b)", "postgresql")
        assert_sql_equal(sql, "'x' || b ( 'x' || b)")

    def test_string_concat_2(self):
        sql = translate("a + ';b'", "postgresql")
        assert_sql_equal(sql, "a || ';b'")

    def test_string_concat_3(self):
        sql = translate("a + ';('", "postgresql")
        assert_sql_equal(sql, "a || ';('")

    def test_dateadd_month(self):
        sql = translate("DATEADD(mm,1,date)", "postgresql")
        assert_sql_equal(sql, "(date + 1*INTERVAL'1 month')")

    def test_datediff_month(self):
        sql = translate(
            "SELECT DATEDIFF(month,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "postgresql",
        )
        expected = (
            "SELECT (extract(year from age(CAST(drug_era_end_date AS DATE),"
            " CAST(drug_era_start_date AS DATE)))*12 + extract(month from age"
            "(CAST(drug_era_end_date AS DATE), CAST(drug_era_start_date AS DATE)))) FROM drug_era;"
        )
        assert_sql_equal(sql, expected)

    def test_getdate(self):
        sql = translate("GETDATE()", "postgresql")
        assert_sql_equal(sql, "CURRENT_DATE")

    def test_select_into_temp(self):
        sql = translate("SELECT a INTO #b FROM c;", "postgresql")
        assert_sql_equal(
            sql,
            "CREATE TEMP TABLE b\nAS\nSELECT\na\nFROM\nc;\nANALYZE b;",
        )

    def test_select_top(self):
        sql = translate("SELECT TOP 10 a FROM b;", "postgresql")
        assert_sql_equal(sql, "SELECT a FROM b LIMIT 10;")

    def test_distinct_top(self):
        sql = translate("SELECT DISTINCT TOP 10 a FROM b;", "postgresql")
        assert_sql_equal(sql, "SELECT DISTINCT a FROM b LIMIT 10;")

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('my_table', 'U') IS NULL CREATE TABLE my_table (id INT);",
            "postgresql",
        )
        assert_sql_equal(sql, "CREATE TABLE IF NOT EXISTS my_table (id INT);")

    def test_drop_table_if_exists(self):
        sql = translate(
            "IF OBJECT_ID('my_table', 'U') IS NOT NULL DROP TABLE my_table;",
            "postgresql",
        )
        assert_sql_equal(sql, "DROP TABLE IF EXISTS my_table;")

    def test_isnull(self):
        sql = translate("ISNULL(a, b)", "postgresql")
        assert_sql_equal(sql, "COALESCE(a, b)")

    def test_round(self):
        sql = translate("ROUND(a, 2)", "postgresql")
        assert_sql_equal(sql, "ROUND(CAST(a AS NUMERIC), 2)")

    def test_len(self):
        sql = translate("LEN('hello')", "postgresql")
        assert_sql_equal(sql, "CHAR_LENGTH('hello')")

    def test_iif(self):
        sql = translate(
            "IIF(a > 0, 'positive', 'non-positive')",
            "postgresql",
        )
        assert_sql_equal(
            sql,
            "CASE WHEN a > 0 THEN 'positive' ELSE 'non-positive' END",
        )

    def test_charindex(self):
        sql = translate("CHARINDEX('needle', haystack)", "postgresql")
        assert_sql_equal(sql, "STRPOS(haystack, 'needle')")

    def test_temp_table_emulation(self):
        sql = translate("SELECT a INTO #temptable FROM b;", "postgresql")
        assert "CREATE TEMP TABLE" in sql
        assert "temptable" in sql.lower()
