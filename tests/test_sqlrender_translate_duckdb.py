"""Test DuckDB translation - ported from OHDSI SqlRender test-translate-duckdb.R"""

import re

from circe.sqlrender import translate

# Force fresh pattern load for each test module


def setup_function():
    global _target_to_patterns
    _target_to_patterns = None


def normalize_sql(s: str) -> str:
    s = re.sub(r"([;()'+\-/|*\n])", r" \1 ", s)
    s = re.sub(r" +", " ", s)
    return s.strip()


def assert_sql_equal(actual: str, expected: str):
    assert normalize_sql(actual) == normalize_sql(expected), f"\nExpected: {expected}\nGot:      {actual}"


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
        expected = "CREATE TABLE d \nAS\nWITH cte1 AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1;"
        assert_sql_equal(sql, expected)

    def test_select_into(self):
        sql = translate("SELECT c INTO d;", "duckdb")
        expected = "CREATE TABLE d AS\nSELECT\nc ;"
        assert_sql_equal(sql, expected)

    def test_cte_insert_into_select(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;",
            "duckdb",
        )
        expected = "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;"
        assert_sql_equal(sql, expected)

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NULL\n CREATE TABLE cohort\n(cohort_definition_id INT);",
            "duckdb",
        )
        expected = "CREATE TABLE IF NOT EXISTS cohort\n (cohort_definition_id INT);"
        assert_sql_equal(sql, expected)

    def test_select_random_row(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RAND()) AS rn FROM table) tmp WHERE rn <= 1",
            "duckdb",
        )
        expected = "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn FROM table) tmp WHERE rn <= 1"
        assert_sql_equal(sql, expected)

    def test_temp_table(self):
        sql = translate("SELECT * FROM #my_temp;", "duckdb")
        assert_sql_equal(sql, "SELECT * FROM my_temp;")

    def test_top(self):
        sql = translate("SELECT TOP 10 * FROM my_table WHERE a = b;", "duckdb")
        assert_sql_equal(sql, "SELECT * FROM my_table WHERE a = b LIMIT 10;")

    def test_top_subquery(self):
        sql = translate(
            "SELECT name FROM (SELECT TOP 1 name FROM my_table WHERE a = b);",
            "duckdb",
        )
        expected = "SELECT name FROM (SELECT name FROM my_table WHERE a = b LIMIT 1);"
        assert_sql_equal(sql, expected)

    def test_convert_varchar_date_112(self):
        sql = translate("CONVERT(VARCHAR,start_date,112) FROM table;", "duckdb")
        assert_sql_equal(sql, "STRFTIME(start_date, '%Y%m%d') FROM table;")

    def test_convert_date(self):
        sql = translate("CONVERT(DATE, '20000101');", "duckdb")
        assert_sql_equal(sql, "CAST(strptime('20000101', '%Y%m%d') AS DATE);")

    def test_cast_date(self):
        sql = translate("CAST('20000101' AS DATE);", "duckdb")
        assert_sql_equal(sql, "CAST(strptime('20000101', '%Y%m%d') AS DATE);")

    def test_log_any_base(self):
        sql = translate("SELECT LOG(number, base) FROM table", "duckdb")
        expected = "SELECT (LN(CAST((number) AS REAL))/LN(CAST((base) AS REAL))) FROM table"
        assert_sql_equal(sql, expected)

    def test_isnumeric(self):
        sql = translate("SELECT CASE WHEN ISNUMERIC(a) = 1 THEN a ELSE b FROM c;", "duckdb")
        expected = (
            "SELECT CASE WHEN CASE WHEN (CAST(a AS VARCHAR) ~ '^([0-9]+\\.?[0-9]*|\\.[0-9]+)$')"
            " THEN 1 ELSE 0 END = 1 THEN a ELSE b FROM c;"
        )
        assert_sql_equal(sql, expected)

    def test_isnumeric_where(self):
        sql = translate("SELECT a FROM table WHERE ISNUMERIC(a) = 1", "duckdb")
        expected = (
            "SELECT a FROM table WHERE CASE WHEN (CAST(a AS VARCHAR) ~ '^([0-9]+\\.?[0-9]*|\\.[0-9]+)$')"
            " THEN 1 ELSE 0 END = 1"
        )
        assert_sql_equal(sql, expected)

    def test_update_statistics(self):
        sql = translate("UPDATE STATISTICS results_schema.heracles_results;", "duckdb")
        assert_sql_equal(sql, "ANALYZE results_schema.heracles_results;")

    def test_datetime_types(self):
        sql = translate("CREATE TABLE x (a DATETIME2, b DATETIME);", "duckdb")
        assert_sql_equal(sql, "CREATE TABLE x (a TIMESTAMP, b TIMESTAMP);")

    def test_getdate(self):
        sql = translate("GETDATE()", "duckdb")
        assert_sql_equal(sql, "CURRENT_DATE")

    def test_create_index(self):
        sql = translate("CREATE INDEX idx_1 ON main.person (person_id);", "duckdb")
        assert_sql_equal(sql, "CREATE INDEX idx_1 ON main.person (person_id);")

    def test_datediff_with_literals(self):
        sql = translate("SELECT DATEDIFF(DAY, '20000131', '20000101');", "duckdb")
        expected = (
            "SELECT (CAST(strptime('20000101', '%Y%m%d') AS DATE)"
            " - CAST(strptime('20000131', '%Y%m%d') AS DATE));"
        )
        assert_sql_equal(sql, expected)

    def test_datediff_date_fields(self):
        sql = translate("SELECT DATEDIFF(DAY, date1, date2);", "duckdb")
        expected = "SELECT (CAST(date2 AS DATE) - CAST(date1 AS DATE));"
        assert_sql_equal(sql, expected)

    def test_datediff_year_literals(self):
        sql = translate("SELECT DATEDIFF(YEAR, '20010131', '20000101');", "duckdb")
        expected = (
            "SELECT (EXTRACT(YEAR FROM CAST(strptime('20000101', '%Y%m%d') AS DATE))"
            " - EXTRACT(YEAR FROM CAST(strptime('20010131', '%Y%m%d') AS DATE)));"
        )
        assert_sql_equal(sql, expected)

    def test_datediff_year_fields(self):
        sql = translate("SELECT DATEDIFF(YEAR, date1, date2);", "duckdb")
        expected = "SELECT (EXTRACT(YEAR FROM CAST(date2 AS DATE)) - EXTRACT(YEAR FROM CAST(date1 AS DATE)));"
        assert_sql_equal(sql, expected)

    def test_datediff_month_literals(self):
        sql = translate("SELECT DATEDIFF(MONTH, '20000115', '20010116');", "duckdb")
        expected = (
            "SELECT (extract(year from age(CAST(strptime('20010116', '%Y%m%d') AS DATE),"
            " CAST(strptime('20000115', '%Y%m%d') AS DATE)))*12"
            " + extract(month from age(CAST(strptime('20010116', '%Y%m%d') AS DATE),"
            " CAST(strptime('20000115', '%Y%m%d') AS DATE))));"
        )
        assert_sql_equal(sql, expected)

    def test_datediff_month_fields(self):
        sql = translate("SELECT DATEDIFF(MONTH, date1, date2);", "duckdb")
        expected = (
            "SELECT (extract(year from age(CAST(date2 AS DATE), CAST(date1 AS DATE)))*12"
            " + extract(month from age(CAST(date2 AS DATE), CAST(date1 AS DATE))));"
        )
        assert_sql_equal(sql, expected)

    def test_ceiling(self):
        sql = translate("SELECT CEILING(0.1);", "duckdb")
        assert_sql_equal(sql, "SELECT CEILING(0.1);")

    def test_drop_table_if_exists(self):
        sql = translate("DROP TABLE IF EXISTS test;", "duckdb")
        assert_sql_equal(sql, "DROP TABLE IF EXISTS test;")

    def test_iif(self):
        sql = translate("SELECT IIF(a>b, 1, b) AS max_val FROM table;", "duckdb")
        expected = "SELECT CASE WHEN a>b THEN 1 ELSE b END AS max_val FROM table ;"
        assert_sql_equal(sql, expected)

    def test_add_days_with_period(self):
        sql = translate("DATEADD(DAY, -2.0, date)", "duckdb")
        assert_sql_equal(sql, "(date + TO_DAYS(CAST(-2.0 AS INTEGER)))")

    def test_newid(self):
        sql = translate("SELECT NEWID()", "duckdb")
        assert_sql_equal(sql, "SELECT uuid()")

    def test_cast_concat_date(self):
        sql = translate("CAST(CONCAT('2000', '0101') AS DATE);", "duckdb")
        assert_sql_equal(sql, "CAST(strptime(CONCAT('2000', '0101'), '%Y%m%d') AS DATE);")

    def test_alter_table_add_single(self):
        sql = translate("ALTER TABLE my_table ADD a INT;", "duckdb")
        assert_sql_equal(sql, "ALTER TABLE my_table  ADD a INT;")

    def test_alter_table_add_multiple(self):
        sql = translate("ALTER TABLE my_table ADD a INT, b INT, c VARCHAR(255);", "duckdb")
        expected = "ALTER TABLE my_table ADD a INT; ALTER TABLE my_table ADD b INT; ALTER TABLE my_table ADD c VARCHAR(255);"
        assert_sql_equal(sql, expected)

    def test_alter_table_alter_column(self):
        sql = translate("ALTER TABLE my_table ALTER COLUMN a BIGINT;", "duckdb")
        assert_sql_equal(sql, "ALTER TABLE my_table ALTER a TYPE BIGINT;")
