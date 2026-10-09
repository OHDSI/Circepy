"""Test SQLite translation - ported from OHDSI SqlRender test-translate-sqlite.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestSQLiteTranslation:
    def test_string_concat_1(self):
        sql = translate("'x' + b ( 'x' + b)", "sqlite")
        assert_sql_equal(sql, "'x' || b ( 'x' || b)")

    def test_string_concat_2(self):
        sql = translate("a + ';b'", "sqlite")
        assert_sql_equal(sql, "a || ';b'")

    def test_string_concat_3(self):
        sql = translate("a + ';('", "sqlite")
        assert_sql_equal(sql, "a || ';('")

    def test_add_month(self):
        sql = translate("DATEADD(mm,1,date)", "sqlite")
        assert_sql_equal(
            sql,
            "CAST(STRFTIME('%s', DATETIME(date, 'unixepoch', (1)||' months')) AS REAL)",
        )

    def test_with_select_into(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "sqlite",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE d \nAS\nWITH cte1 AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1;",
        )

    def test_with_select_into_without_from(self):
        sql = translate("SELECT c INTO d;", "sqlite")
        assert_sql_equal(sql, "CREATE TABLE d AS\nSELECT\nc ;")

    def test_with_insert_into_select(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;",
            "sqlite",
        )
        assert_sql_equal(
            sql,
            "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;",
        )

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NULL\n CREATE TABLE cohort\n(cohort_definition_id INT);",
            "sqlite",
        )
        assert_sql_equal(sql, "CREATE TABLE IF NOT EXISTS cohort\n (cohort_definition_id INT);")

    def test_select_random_row(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RAND()) AS rn FROM table) tmp WHERE rn <= 1",
            "sqlite",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY ((RANDOM()+9223372036854775808) / 18446744073709551615)) AS rn FROM table) tmp WHERE rn <= 1",
        )

    def test_temp_table(self):
        sql = translate("SELECT * FROM #my_temp;", "sqlite")
        assert_sql_equal(sql, "SELECT * FROM temp.my_temp;")

    def test_top(self):
        sql = translate("SELECT TOP 10 * FROM my_table WHERE a = b;", "sqlite")
        assert_sql_equal(sql, "SELECT * FROM my_table WHERE a = b LIMIT 10;")

    def test_top_subquery(self):
        sql = translate(
            "SELECT name FROM (SELECT TOP 1 name FROM my_table WHERE a = b);",
            "sqlite",
        )
        assert_sql_equal(
            sql,
            "SELECT name FROM (SELECT name FROM my_table WHERE a = b LIMIT 1);",
        )

    def test_date_to_string(self):
        sql = translate("SELECT CONVERT(VARCHAR,start_date,112) FROM table;", "sqlite")
        assert_sql_equal(
            sql,
            "SELECT CAST(STRFTIME('%Y%m%d', start_date) AS REAL) FROM table;",
        )

    def test_convert_as_date_1(self):
        sql = translate("CONVERT(DATE, '20000101');", "sqlite")
        assert_sql_equal(
            sql,
            "CAST(STRFTIME('%s', SUBSTR(CAST('20000101' AS TEXT), 1, 4) || '-' || SUBSTR(CAST('20000101' AS TEXT), 5, 2) || '-' || SUBSTR(CAST('20000101' AS TEXT), 7)) AS REAL);",
        )

    def test_convert_as_date_2(self):
        sql = translate("CAST('20000101' AS DATE);", "sqlite")
        assert_sql_equal(
            sql,
            "CAST(STRFTIME('%s', SUBSTR(CAST('20000101' AS TEXT), 1, 4) || '-' || SUBSTR(CAST('20000101' AS TEXT), 5, 2) || '-' || SUBSTR(CAST('20000101' AS TEXT), 7)) AS REAL);",
        )

    def test_log_any_base(self):
        sql = translate("SELECT LOG(number, base) FROM table", "sqlite")
        assert_sql_equal(sql, "SELECT (LOG(number)/LOG(base)) FROM table")

    def test_isnumeric(self):
        sql = translate(
            "SELECT CASE WHEN ISNUMERIC(a) = 1 THEN a ELSE b FROM c;",
            "sqlite",
        )
        assert_sql_equal(
            sql,
            "SELECT CASE WHEN CASE WHEN a GLOB '[0-9]*' OR a GLOB '[0-9]*.[0-9]*' OR a GLOB '.[0-9]*' THEN 1 ELSE 0 END = 1 THEN a ELSE b FROM c;",
        )

        sql = translate("SELECT a FROM table WHERE ISNUMERIC(a) = 1", "sqlite")
        assert_sql_equal(
            sql,
            "SELECT a FROM table WHERE CASE WHEN a GLOB '[0-9]*' OR a GLOB '[0-9]*.[0-9]*' OR a GLOB '.[0-9]*' THEN 1 ELSE 0 END = 1",
        )

    def test_analyze_table(self):
        sql = translate("UPDATE STATISTICS results_schema.heracles_results;", "sqlite")
        assert_sql_equal(sql, "ANALYZE results_schema.heracles_results;")

    def test_datetime_and_datetime2(self):
        sql = translate("CREATE TABLE x (a DATETIME2, b DATETIME);", "sqlite")
        assert_sql_equal(sql, "CREATE TABLE x (a REAL, b REAL);")

    def test_getdate(self):
        sql = translate("GETDATE()", "sqlite")
        assert_sql_equal(sql, "STRFTIME('%s','now')")

    def test_create_index(self):
        sql = translate("CREATE INDEX idx_1 ON main.person (person_id);", "sqlite")
        assert_sql_equal(sql, "CREATE INDEX idx_1  ON person  (person_id);")

    def test_datediff_with_literals(self):
        sql = translate("SELECT DATEDIFF(DAY, '20000131', '20000101');", "sqlite")
        assert_sql_equal(
            sql,
            "SELECT (JULIANDAY(CAST(STRFTIME('%s', SUBSTR(CAST('20000101' AS TEXT), 1, 4) || '-' || SUBSTR(CAST('20000101' AS TEXT), 5, 2) || '-' || SUBSTR(CAST('20000101' AS TEXT), 7)) AS REAL), 'unixepoch') - JULIANDAY(CAST(STRFTIME('%s', SUBSTR(CAST('20000131' AS TEXT), 1, 4) || '-' || SUBSTR(CAST('20000131' AS TEXT), 5, 2) || '-' || SUBSTR(CAST('20000131' AS TEXT), 7)) AS REAL), 'unixepoch'));",
        )

    def test_datediff_with_date_fields(self):
        sql = translate("SELECT DATEDIFF(DAY, date1, date2);", "sqlite")
        assert_sql_equal(
            sql,
            "SELECT (JULIANDAY(date2, 'unixepoch') - JULIANDAY(date1, 'unixepoch'));",
        )

    def test_datediff_year_with_literals(self):
        sql = translate("SELECT DATEDIFF(YEAR, '20010131', '20000101');", "sqlite")
        assert_sql_equal(
            sql,
            "SELECT (CAST(SUBSTR('20000101', 1, 4) AS REAL) - CAST(SUBSTR('20010131', 1, 4) AS REAL));",
        )

    def test_datediff_year_with_date_fields(self):
        sql = translate("SELECT DATEDIFF(YEAR, date1, date2);", "sqlite")
        assert_sql_equal(
            sql,
            "SELECT (STRFTIME('%Y', date2, 'unixepoch') - STRFTIME('%Y', date1, 'unixepoch'));",
        )

    def test_datediff_month_literals(self):
        sql = translate("SELECT DATEDIFF(MONTH, '20000115', '20010116');", "sqlite")
        assert_sql_equal(
            sql,
            "SELECT ((CAST(SUBSTR('20010116', 1, 4) AS REAL)*12 + CAST(SUBSTR('20010116', 5, 2) AS REAL)) - (CAST(SUBSTR('20000115', 1, 4) AS REAL)*12 + CAST(SUBSTR('20000115', 5, 2) AS REAL)) + (CASE WHEN CAST(SUBSTR('20010116', 7, 2) AS REAL) >= CAST(SUBSTR('20000115', 7, 2) AS REAL) then 0 else -1 end));",
        )

    def test_datediff_month_date_fields(self):
        sql = translate("SELECT DATEDIFF(MONTH, date1, date2);", "sqlite")
        assert_sql_equal(
            sql,
            "SELECT ((STRFTIME('%Y', date2, 'unixepoch')*12 + STRFTIME('%m', date2, 'unixepoch')) - (STRFTIME('%Y', date1, 'unixepoch')*12 + STRFTIME('%m', date1, 'unixepoch')) + (CASE WHEN STRFTIME('%d', date2, 'unixepoch') >= STRFTIME('%d', date1, 'unixepoch') then 0 else -1 end));",
        )

    def test_ceiling(self):
        sql = translate("SELECT CEILING(0.1);", "sqlite")
        assert_sql_equal(sql, "SELECT CEIL(0.1);")

    def test_drop_table_if_exists(self):
        sql = translate("DROP TABLE IF EXISTS test;", "sqlite")
        assert_sql_equal(sql, "DROP TABLE IF EXISTS test;")

    def test_iif(self):
        sql = translate("SELECT IIF(a>b, 1, b) AS max_val FROM table;", "sqlite")
        assert_sql_equal(sql, "SELECT CASE WHEN a>b THEN 1 ELSE b END AS max_val FROM table ;")

    def test_union_all_parentheses(self):
        sql = translate(
            "SELECT * FROM ((SELECT * FROM a) UNION ALL (SELECT * FROM b));",
            "sqlite",
        )
        assert_sql_equal(sql, "SELECT * FROM (SELECT * FROM a UNION ALL SELECT * FROM b);")

    def test_union_parentheses(self):
        sql = translate(
            "SELECT * FROM ((SELECT * FROM a) UNION (SELECT * FROM b));",
            "sqlite",
        )
        assert_sql_equal(sql, "SELECT * FROM (SELECT * FROM a UNION SELECT * FROM b);")

    def test_union_parentheses_with_in(self):
        sql = translate(
            "SELECT * FROM x WHERE y IN (SELECT * FROM a) UNION SELECT * FROM z;",
            "sqlite",
        )
        assert_sql_equal(
            sql,
            "SELECT * FROM x WHERE y IN ((SELECT * FROM a)) UNION SELECT * FROM z;",
        )

    def test_try_cast(self):
        sql = translate("SELECT TRY_CAST(x AS INT) FROM x;", "sqlite")
        assert_sql_equal(sql, "SELECT CAST(x AS INT) FROM x;")

    def test_drvd(self):
        sql = translate(
            "SELECT\n      TRY_CAST(name AS VARCHAR(MAX)) AS name,\n      TRY_CAST(speed AS FLOAT) AS speed\n    FROM (  VALUES ('A', 1.0), ('B', 2.0)) AS drvd(name, speed);",
            "sqlite",
        )
        assert_sql_equal(
            sql,
            "SELECT\n      CAST(name AS TEXT) AS name,\n      CAST(speed AS REAL) AS speed\n    FROM (SELECT NULL AS name, NULL AS speed WHERE (0 = 1) UNION ALL VALUES ('A', 1.0), ('B', 2.0)) AS values_table;",
        )

    def test_temp_table_field_ref(self):
        sql = translate("SELECT #tmp.name FROM #tmp;", "sqlite")
        assert_sql_equal(sql, "SELECT tmp.name FROM temp.tmp;")

    def test_alter_table_add_single(self):
        sql = translate("ALTER TABLE my_table ADD a INT;", "sqlite")
        assert_sql_equal(sql, "ALTER TABLE my_table  ADD a INT;")

    def test_alter_table_add_multiple(self):
        sql = translate("ALTER TABLE my_table ADD a INT, b INT, c VARCHAR(255);", "sqlite")
        assert_sql_equal(
            sql,
            "ALTER TABLE my_table ADD a INT; ALTER TABLE my_table ADD b INT; ALTER TABLE my_table ADD c TEXT;",
        )

    def test_alter_table_add_column(self):
        sql = translate("ALTER TABLE my_table ADD COLUMN a INT;", "sqlite")
        assert_sql_equal(sql, "ALTER TABLE my_table ADD COLUMN a INT;")

    def test_alter_table_alter_column(self):
        sql = translate("ALTER TABLE my_table ALTER COLUMN a BIGINT;", "sqlite")
        assert_sql_equal(sql, "SELECT 0;")
