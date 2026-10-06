"""Test SQLite Extended translation - ported from OHDSI SqlRender test-translate-sqlite-extended.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestSQLiteExtendedTranslation:
    def test_string_concat_1(self):
        sql = translate("'x' + b ( 'x' + b)", "sqlite extended")
        assert_sql_equal(sql, "'x' || b ( 'x' || b)")

    def test_string_concat_2(self):
        sql = translate("a + ';b'", "sqlite extended")
        assert_sql_equal(sql, "a || ';b'")

    def test_string_concat_3(self):
        sql = translate("a + ';('", "sqlite extended")
        assert_sql_equal(sql, "a || ';('")

    def test_with_select_into(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "sqlite extended",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE d \nAS\nWITH cte1 AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1;",
        )

    def test_with_select_into_without_from(self):
        sql = translate("SELECT c INTO d;", "sqlite extended")
        assert_sql_equal(sql, "CREATE TABLE d AS\nSELECT\nc ;")

    def test_with_insert_into_select(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;",
            "sqlite extended",
        )
        assert_sql_equal(
            sql,
            "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;",
        )

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NULL\n CREATE TABLE cohort\n(cohort_definition_id INT);",
            "sqlite extended",
        )
        assert_sql_equal(sql, "CREATE TABLE IF NOT EXISTS cohort\n (cohort_definition_id INT);")

    def test_select_random_row(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RAND()) AS rn FROM table) tmp WHERE rn <= 1",
            "sqlite extended",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn FROM table) tmp WHERE rn <= 1",
        )

    def test_temp_table(self):
        sql = translate("SELECT * FROM #my_temp;", "sqlite extended")
        assert_sql_equal(sql, "SELECT * FROM temp.my_temp;")

    def test_top(self):
        sql = translate("SELECT TOP 10 * FROM my_table WHERE a = b;", "sqlite extended")
        assert_sql_equal(sql, "SELECT * FROM my_table WHERE a = b LIMIT 10;")

    def test_top_subquery(self):
        sql = translate(
            "SELECT name FROM (SELECT TOP 1 name FROM my_table WHERE a = b);",
            "sqlite extended",
        )
        assert_sql_equal(
            sql,
            "SELECT name FROM (SELECT name FROM my_table WHERE a = b LIMIT 1);",
        )

    def test_log_any_base(self):
        sql = translate("SELECT LOG(number, base) FROM table", "sqlite extended")
        assert_sql_equal(sql, "SELECT (LOG(number)/LOG(base)) FROM table")

    def test_isnumeric(self):
        sql = translate(
            "SELECT CASE WHEN ISNUMERIC(a) = 1 THEN a ELSE b FROM c;",
            "sqlite extended",
        )
        assert_sql_equal(
            sql,
            "SELECT CASE WHEN CASE WHEN a GLOB '[0-9]*' OR a GLOB '[0-9]*.[0-9]*' OR a GLOB '.[0-9]*' THEN 1 ELSE 0 END = 1 THEN a ELSE b FROM c;",
        )

        sql = translate("SELECT a FROM table WHERE ISNUMERIC(a) = 1", "sqlite extended")
        assert_sql_equal(
            sql,
            "SELECT a FROM table WHERE CASE WHEN a GLOB '[0-9]*' OR a GLOB '[0-9]*.[0-9]*' OR a GLOB '.[0-9]*' THEN 1 ELSE 0 END = 1",
        )

    def test_analyze_table(self):
        sql = translate(
            "UPDATE STATISTICS results_schema.heracles_results;",
            "sqlite extended",
        )
        assert_sql_equal(sql, "ANALYZE results_schema.heracles_results;")

    def test_create_index(self):
        sql = translate(
            "CREATE INDEX idx_1 ON main.person (person_id);",
            "sqlite extended",
        )
        assert_sql_equal(sql, "CREATE INDEX idx_1  ON person  (person_id);")

    def test_drop_table_if_exists(self):
        sql = translate("DROP TABLE IF EXISTS test;", "sqlite extended")
        assert_sql_equal(sql, "DROP TABLE IF EXISTS test;")
