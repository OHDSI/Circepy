"""Test Spark translation - ported from OHDSI SqlRender test-translate-spark.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestSparkTranslation:
    def test_round(self):
        sql = translate("SELECT round(3.14, 1)", "spark")
        assert_sql_equal(sql, "SELECT ROUND(CAST(3.14 AS DOUBLE),1)")

    def test_select_random_row_using_hash(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY HASHBYTES('MD5',CAST(person_id AS varchar))) tmp WHERE rn <= 1",
            "spark",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY MD5(CAST(person_id AS STRING))) tmp WHERE rn <= 1",
        )

    def test_convert_varbinary(self):
        sql = translate(
            "SELECT ROW_NUMBER() OVER CONVERT(VARBINARY, val, 1) rn WHERE rn <= 1",
            "spark",
        )
        assert_sql_equal(
            sql,
            "SELECT ROW_NUMBER() OVER CONVERT(VARBINARY, val, 1) rn WHERE rn <= 1",
        )

    def test_convert_date(self):
        sql = translate("SELECT convert(date, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT TO_DATE('2019-01-01', 'yyyy-MM-dd')")

    def test_dateadd(self):
        sql = translate("SELECT DATEADD(second, -1 * 2, '2019-01-01 00:00:00')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(second, -1 * 2, '2019-01-01 00:00:00')")

        sql = translate("SELECT DATEADD(minute, -1 * 3, '2019-01-01 00:00:00')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(minute, -1 * 3, '2019-01-01 00:00:00')")

        sql = translate("SELECT DATEADD(hour, -1 * 4, '2019-01-01 00:00:00')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(hour, -1 * 4, '2019-01-01 00:00:00')")

        sql = translate("SELECT DATEADD(second, 1, '2019-01-01 00:00:00')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(second, 1, '2019-01-01 00:00:00')")

        sql = translate("SELECT DATEADD(minute, 1, '2019-01-01 00:00:00')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(minute, 1, '2019-01-01 00:00:00')")

        sql = translate("SELECT DATEADD(hour, 1, '2019-01-01 00:00:00')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(hour, 1, '2019-01-01 00:00:00')")

        sql = translate("SELECT DATEADD(d, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(day, 1, '2019-01-01')")

        sql = translate("SELECT DATEADD(dd, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(day, 1, '2019-01-01')")

        sql = translate("SELECT DATEADD(day, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(day, 1, '2019-01-01')")

        sql = translate("SELECT DATEADD(m, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(month, 1, '2019-01-01')")

        sql = translate("SELECT DATEADD(mm, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(month, 1, '2019-01-01')")

        sql = translate("SELECT DATEADD(month, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(month, 1, '2019-01-01')")

        sql = translate("SELECT DATEADD(yy, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(year, 1, '2019-01-01')")

        sql = translate("SELECT DATEADD(yyyy, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(year, 1, '2019-01-01')")

        sql = translate("SELECT DATEADD(year, 1, '2019-01-01')", "spark")
        assert_sql_equal(sql, "SELECT DATEADD(year, 1, '2019-01-01')")

    def test_datediff(self):
        sql = translate("SELECT datediff(d, '2019-01-01', '2019-01-02')", "spark")
        assert_sql_equal(
            sql,
            "SELECT datediff(day, '2019-01-01', '2019-01-02')",
        )

        sql = translate("SELECT datediff(dd, '2019-01-01', '2019-01-02')", "spark")
        assert_sql_equal(
            sql,
            "SELECT datediff(day, '2019-01-01', '2019-01-02')",
        )

    def test_convert_varchar(self):
        sql = translate("select convert(varchar,'2019-01-01',112)", "spark")
        assert_sql_equal(sql, "select '2019-01-01'")

    def test_getdate(self):
        sql = translate("select GETDATE()", "spark")
        assert_sql_equal(sql, "select CURRENT_DATE")

    def test_concat(self):
        sql = translate("select 'oh' + 'dsi'", "spark")
        assert_sql_equal(sql, "select 'oh' || 'dsi'")

    def test_cast_varchar_and_concat(self):
        sql = translate("select cast('test' as varchar(10)) + 'ing'", "spark")
        assert_sql_equal(sql, "select cast('test' as STRING) || 'ing'")

    def test_date_from_parts(self):
        sql = translate("select datefromparts('2019','01','01')", "spark")
        assert_sql_equal(
            sql,
            "select to_date(cast('2019' as string) || '-' || cast('01' as string) || '-' || cast('01' as string))",
        )

    def test_datetime_from_parts(self):
        sql = translate(
            "select datetimefromparts('2019', '01', '01', '12', '15', '30', '01')",
            "spark",
        )
        assert_sql_equal(
            sql,
            "select to_timestamp(cast('2019' as string) || '-' || cast('01' as string) || '-' || cast('01' as string) || ' ' || cast('12' as string) || ':' || cast('15' as string) || ':' || cast('30' as string) || '.' || cast('01' as string))",
        )

    def test_eomonth(self):
        sql = translate("select eomonth('2019-01-01')", "spark")
        assert_sql_equal(sql, "select last_day('2019-01-01')")

    def test_stdev(self):
        sql = translate("select STDEV(x)", "spark")
        assert_sql_equal(sql, "select STDDEV(x)")

    def test_var(self):
        sql = translate("select VAR(x)", "spark")
        assert_sql_equal(sql, "select VARIANCE(x)")

    def test_len(self):
        sql = translate("select LEN(x)", "spark")
        assert_sql_equal(sql, "select LENGTH(x)")

    def test_charindex(self):
        sql = translate("select CHARINDEX('test', 'e')", "spark")
        assert_sql_equal(sql, "select INSTR('e', 'test')")

    def test_log(self):
        sql = translate("select LOG(x,y)", "spark")
        assert_sql_equal(sql, "select LOG(y,x)")

        sql = translate("select LOG(x)", "spark")
        assert_sql_equal(sql, "select LN(x)")

        sql = translate("select LOG10(x)", "spark")
        assert_sql_equal(sql, "select LOG(10,x)")

    def test_isnull(self):
        sql = translate("select ISNULL(x,y)", "spark")
        assert_sql_equal(sql, "select COALESCE(x,y)")

    def test_isnumeric(self):
        sql = translate("select ISNUMERIC(x)", "spark")
        assert_sql_equal(
            sql,
            "select CASE WHEN CAST(x AS DOUBLE) IS NOT NULL THEN 1 ELSE 0 END",
        )

    def test_count_big(self):
        sql = translate("select COUNT_BIG(x)", "spark")
        assert_sql_equal(sql, "select COUNT(x)")

    def test_square(self):
        sql = translate("select SQUARE(x)", "spark")
        assert_sql_equal(sql, "select ((x)*(x))")

    def test_newid(self):
        sql = translate("select NEWID()", "spark")
        assert_sql_equal(sql, "select UUID()")

    def test_if_object_id(self):
        sql = translate(
            "IF OBJECT_ID('some_table', 'U') IS NULL CREATE TABLE some_table (id int);",
            "spark",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE IF NOT EXISTS some_table  \nUSING DELTA\nAS\nSELECT\nCAST(NULL AS int) AS id  WHERE 1 = 0;",
        )

        sql = translate(
            "IF OBJECT_ID('some_table', 'U') IS NOT NULL DROP TABLE some_table;",
            "spark",
        )
        assert_sql_equal(sql, "DROP TABLE IF EXISTS some_table;")

    def test_dbo(self):
        sql = translate("select * from cdm.dbo.test", "spark")
        assert_sql_equal(sql, "select * from cdm.test")

    def test_table_admin(self):
        sql = translate(
            "CREATE CLUSTERED INDEX index_name ON some_table (variable);",
            "spark",
        )
        assert_sql_equal(sql, "")

        sql = translate(
            "CREATE UNIQUE CLUSTERED INDEX index_name ON some_table (variable);",
            "spark",
        )
        assert_sql_equal(sql, "")

        sql = translate("PRIMARY KEY NONCLUSTERED", "spark")
        assert_sql_equal(sql, "")

        sql = translate("UPDATE STATISTICS test;", "spark")
        assert_sql_equal(sql, "")

    def test_datetime(self):
        sql = translate("DATETIME", "spark")
        assert_sql_equal(sql, "TIMESTAMP")

        sql = translate("DATETIME2", "spark")
        assert_sql_equal(sql, "TIMESTAMP")

    def test_varchar(self):
        sql = translate("VARCHAR(MAX)", "spark")
        assert_sql_equal(sql, "STRING")

        sql = translate("VARCHAR", "spark")
        assert_sql_equal(sql, "STRING")

        sql = translate("VARCHAR(100)", "spark")
        assert_sql_equal(sql, "STRING")

    def test_cte_ctas(self):
        sql = translate(
            "WITH a AS (select b) SELECT c INTO d FROM e;",
            "spark",
        )
        assert_sql_equal(
            sql,
            "DROP VIEW IF EXISTS a ; CREATE TEMPORARY VIEW a  AS (select b);\n CREATE TABLE d \nUSING DELTA\nAS\n(SELECT\nc \nFROM\ne);",
        )

    def test_ctas(self):
        sql = translate("SELECT a INTO b FROM c;", "spark")
        assert_sql_equal(
            sql,
            "CREATE TABLE b \nUSING DELTA\nAS\nSELECT\na \nFROM\nc;",
        )

    def test_ctas_with_distribute_on_key(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(key)\n                          SELECT a INTO b FROM c;",
            "spark",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(key) \nCREATE TABLE b \nUSING DELTA\nAS\nSELECT\na \nFROM\nc;\nOPTIMIZE b  ZORDER BY key;",
        )

    def test_cross_join(self):
        sql = translate(
            "SELECT a from (select b) x, (select c) y;",
            "spark",
        )
        assert_sql_equal(
            sql,
            "SELECT a  FROM (select b) x cross join (select c) y;",
        )

    def test_drop_table_if_exists(self):
        sql = translate("DROP TABLE IF EXISTS test;", "spark")
        assert_sql_equal(sql, "DROP TABLE IF EXISTS test;")

    def test_double_cte_insert_into(self):
        sql = translate(
            "WITH a AS (\n"
            "    SELECT * FROM my_table_1\n"
            "  ), b AS (\n"
            "    SELECT * FROM my_table_2\n"
            "  )\n"
            "  SELECT *\n"
            "  INTO some_table\n"
            "  FROM a, b;",
            "spark",
        )
        assert_sql_equal(
            sql,
            "DROP VIEW IF EXISTS a  ; CREATE TEMPORARY VIEW a   AS (SELECT * FROM my_table_1\n );\n"
            "DROP VIEW IF EXISTS b ; CREATE TEMPORARY VIEW b  AS (SELECT * FROM my_table_2\n );\n"
            " CREATE TABLE some_table \nUSING DELTA\nAS\n(SELECT\n*\nFROM\na, b);",
        )

    def test_iif(self):
        sql = translate("SELECT IIF(a>b, 1, b) AS max_val FROM table;", "spark")
        assert_sql_equal(
            sql,
            "SELECT CASE WHEN a>b THEN 1 ELSE b END AS max_val FROM table;",
        )

    def test_datepart(self):
        sql = translate("select DATEPART(YEAR, some_date) from my_table", "spark")
        assert_sql_equal(
            sql,
            "select DATE_PART('YEAR', some_date) from my_table",
        )

    def test_dateadd_day_with_float(self):
        sql = translate("select DATEADD(DAY, 1.0, some_date) from my_table;", "spark")
        assert_sql_equal(
            sql,
            "select CAST(DATEADD(DAY, 1, some_date) AS DATE) from my_table;",
        )

    def test_dateadd_year_with_float(self):
        sql = translate("select DATEADD(YEAR, 1.0, some_date) from my_table;", "spark")
        assert_sql_equal(
            sql,
            "select CAST(DATEADD(YEAR, 1, some_date) AS DATE) from my_table;",
        )

    def test_cte(self):
        sql = translate(
            "WITH cte AS (SELECT * FROM table) SELECT * INTO tmp.table FROM cte;",
            "spark",
        )
        assert_sql_equal(
            sql,
            "DROP VIEW IF EXISTS cte ; CREATE TEMPORARY VIEW cte  AS (SELECT * FROM table);\n"
            " CREATE TABLE tmp.table \nUSING DELTA\nAS\n(SELECT\n* \nFROM\ncte);",
        )

    def test_temp_table_field_ref(self):
        sql = translate(
            "SELECT #tmp.name FROM #tmp;",
            "spark",
            temp_emulation_schema="ts",
            session_id="T0000000",
        )
        assert_sql_equal(
            sql,
            "SELECT T0000000tmp.name FROM ts.T0000000tmp;",
        )

    def test_add_column_with_default(self):
        sql = translate("ALTER TABLE mytable ADD COLUMN mycol int DEFAULT 0;", "spark")
        assert_sql_equal(
            sql,
            "ALTER TABLE mytable ADD COLUMN mycol int; \n"
            " ALTER TABLE mytable SET TBLPROPERTIES('delta.feature.allowColumnDefaults' = 'supported'); \n"
            " ALTER TABLE mytable ALTER COLUMN mycol SET DEFAULT 0;",
        )

    def test_cast_string_as_date(self):
        sql = translate("SELECT CAST('20191201' AS DATE);", "spark")
        assert_sql_equal(
            sql,
            "SELECT IF(try_cast('20191201' AS DATE) IS NULL, "
            "to_date(cast('20191201' AS STRING), 'yyyyMMdd'), "
            "try_cast('20191201' AS DATE));",
        )

    def test_create_temp_table(self):
        sql = translate(
            "CREATE TABLE #temp (x INT);",
            "spark",
            temp_emulation_schema="ts",
            session_id="T0000000",
        )
        assert_sql_equal(
            sql,
            "DROP TABLE IF EXISTS ts.T0000000temp;\n"
            "CREATE TABLE ts.T0000000temp  \nUSING DELTA\n AS\n"
            "SELECT\nCAST(NULL AS int) AS x  WHERE 1 = 0;",
        )

    def test_select_into_temp_table(self):
        sql = translate(
            "SELECT * INTO #temp FROM my_table;",
            "spark",
            temp_emulation_schema="ts",
            session_id="T0000000",
        )
        assert_sql_equal(
            sql,
            "DROP TABLE IF EXISTS ts.T0000000temp;\n"
            "CREATE TABLE ts.T0000000temp \nUSING DELTA\nAS\n"
            "SELECT\n* \nFROM\nmy_table;",
        )

    def test_create_temp_table_if_not_exists(self):
        sql = translate(
            "CREATE TABLE IF NOT EXISTS #temp (x INT);",
            "spark",
            temp_emulation_schema="ts",
            session_id="T0000000",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE IF NOT EXISTS ts.T0000000temp  \nUSING DELTA\n AS\n"
            "SELECT\nCAST(NULL AS int) AS x  WHERE 1 = 0;",
        )

    def test_dateadd_for_date_column(self):
        sql = translate("SELECT DATEADD(DAY, 1, start_date) FROM table;", "spark")
        assert_sql_equal(
            sql,
            "SELECT CAST(DATEADD(DAY, 1, start_date) AS DATE) FROM table;",
        )

        sql = translate("SELECT DATEADD(DAY, 1, START_DATE) FROM table;", "spark")
        assert_sql_equal(
            sql,
            "SELECT CAST(DATEADD(DAY, 1, START_DATE) AS DATE) FROM table;",
        )

        sql = translate("SELECT DATEADD(DAY, 1, start_datetime) FROM table;", "spark")
        assert_sql_equal(
            sql,
            "SELECT DATEADD(DAY, 1, start_datetime) FROM table;",
        )

    def test_create_table_with_float(self):
        sql = translate("CREATE TABLE a.b (x FLOAT);", "spark")
        assert_sql_equal(
            sql,
            "CREATE TABLE a.b  \nUSING DELTA\n AS\nSELECT\nCAST(NULL AS DOUBLE) AS x  WHERE 1 = 0;",
        )
