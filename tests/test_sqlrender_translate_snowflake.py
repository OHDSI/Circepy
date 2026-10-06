"""Test Snowflake translation - ported from OHDSI SqlRender test-translate-snowflake.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestSnowflakeTranslation:
    def test_select_random_row_using_hash(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY HASHBYTES('MD5',CAST(person_id AS varchar))) tmp WHERE rn <= 1",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY MD5(CAST(person_id AS varchar))) tmp WHERE rn <= 1",
        )

    def test_convert_varbinary(self):
        sql = translate(
            "SELECT ROW_NUMBER() OVER CONVERT(VARBINARY, val, 1) rn WHERE rn <= 1",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "SELECT ROW_NUMBER() OVER CAST(CONCAT('x', val) AS BIT(32)) rn WHERE rn <= 1",
        )

    def test_clustered_index_not_supported(self):
        sql = translate(
            "CREATE CLUSTERED INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "snowflake",
        )
        assert_sql_equal(sql, "-- snowflake does not support indexes")

    def test_index_not_supported(self):
        sql = translate(
            "CREATE INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "snowflake",
        )
        assert_sql_equal(sql, "-- snowflake does not support indexes")

    def test_use(self):
        sql = translate("USE vocabulary;", "snowflake")
        assert_sql_equal(sql, "USE vocabulary;")

    def test_insert_into_with(self):
        sql = translate(
            "WITH a AS (SELECT * FROM b) INSERT INTO c SELECT * FROM a;",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "INSERT INTO c WITH a AS (SELECT * FROM b) SELECT * FROM a;",
        )

    def test_with_select_into(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE d \nAS\nWITH cte1  AS (SELECT a FROM b)  SELECT\nc\nFROM\ncte1;",
        )

    def test_with_select_into_without_from(self):
        sql = translate("SELECT c INTO d;", "snowflake")
        assert_sql_equal(
            sql,
            "CREATE TABLE d AS\nSELECT\nc ;",
        )

    def test_location_reserved_word(self):
        sql = translate("select count(1) from omop_cdm.location;", "snowflake")
        assert_sql_equal(sql, "select count(1) from omop_cdm.location;")

    def test_top_in_subqueries(self):
        sql = translate(
            "select statistic_value from achilles_results join (SELECT TOP 1 count as total_pts from achilles_results where analysis_id = 1) where analysis_id in (2002,2003)",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "select statistic_value from achilles_results join (SELECT  count as total_pts from achilles_results where analysis_id = 1 LIMIT 1) where analysis_id in (2002,2003)",
        )

    def test_create_table_with_not_null(self):
        sql = translate(
            "CREATE TABLE a (c1 BIGINT NOT NULL, c2 BOOLEAN NOT NULL, c3 CHAR NOT NULL, c4 DECIMAL NOT NULL, c5 DOUBLE NOT NULL, c6 FLOAT NOT NULL, c7 INT NOT NULL, c8 REAL NOT NULL, c9 SMALLINT NOT NULL, c10 STRING NOT NULL, c11 TIMESTAMP NOT NULL, c12 TINYINT NOT NULL, c13 VARCHAR(10) NOT NULL, c14 DATE NOT NULL, c15 DATETIME NOT NULL, c16 INTEGER NOT NULL)",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE a (c1 BIGINT NOT NULL, c2 BOOLEAN NOT NULL, c3 CHAR NOT NULL, c4 DECIMAL NOT NULL, c5 DOUBLE NOT NULL, c6 FLOAT NOT NULL, c7 INT NOT NULL, c8 REAL NOT NULL, c9 SMALLINT NOT NULL, c10 STRING NOT NULL, c11 TIMESTAMP NOT NULL, c12 TINYINT NOT NULL, c13 VARCHAR(10) NOT NULL, c14 DATE NOT NULL, c15 TIMESTAMP NOT NULL, c16 INTEGER NOT NULL)",
        )

    def test_create_table_with_null(self):
        sql = translate(
            "CREATE TABLE a (c1 BIGINT NULL, c2 BOOLEAN NULL, c3 CHAR NULL, c4 DECIMAL NULL, c5 DOUBLE NULL, c6 FLOAT NULL, c7 INT NULL, c8 REAL NULL, c9 SMALLINT NULL, c10 STRING NULL, c11 TIMESTAMP NULL, c12 TINYINT NULL, c13 VARCHAR(10) NULL, c14 DATE NULL, c15 DATETIME NULL)",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE a (c1 BIGINT NULL, c2 BOOLEAN NULL, c3 CHAR NULL, c4 DECIMAL NULL, c5 DOUBLE NULL, c6 FLOAT NULL, c7 INT NULL, c8 REAL NULL, c9 SMALLINT NULL, c10 STRING NULL, c11 TIMESTAMP NULL, c12 TINYINT NULL, c13 VARCHAR(10) NULL, c14 DATE NULL, c15 TIMESTAMP NULL)",
        )

    def test_clause_with_not_null(self):
        sql = translate("SELECT * FROM x WHERE y IS NOT NULL", "snowflake")
        assert_sql_equal(sql, "SELECT * FROM x WHERE y IS NOT NULL")

    def test_create_table_with_constraint_default_1(self):
        sql = translate(
            "CREATE TABLE a(c1 TIMESTAMP CONSTRAINT a_c1_def DEFAULT NOW())",
            "snowflake",
        )
        assert_sql_equal(sql, "CREATE TABLE a(c1 TIMESTAMP CONSTRAINT a_c1_def DEFAULT NOW())")

    def test_create_table_with_constraint_default_2(self):
        sql = translate("CREATE TABLE a(c1 TIMESTAMP DEFAULT NOW())", "snowflake")
        assert_sql_equal(sql, "CREATE TABLE a(c1 TIMESTAMP DEFAULT NOW())")

    def test_datefromparts(self):
        sql = translate("SELECT DATEFROMPARTS('1977', '10', '12')", "snowflake")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(TO_CHAR('1977','FM0000')||'-'||TO_CHAR('10','FM00')||'-'||TO_CHAR('12','FM00'), 'YYYY-MM-DD')",
        )

    def test_eomonth(self):
        sql = translate(
            "SELECT eomonth(payer_plan_period_start_date) AS obs_month_end",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "SELECT last_day(payer_plan_period_start_date) AS obs_month_end",
        )

    def test_isnumeric(self):
        sql = translate("SELECT ISNUMERIC(a) FROM b", "snowflake")
        assert_sql_equal(sql, "SELECT IS_REAL(TRY_TO_NUMERIC(a)) FROM b")

        sql = translate("SELECT some FROM table WHERE ISNUMERIC(a) = 1", "snowflake")
        assert_sql_equal(sql, "SELECT some FROM table WHERE IS_REAL(TRY_TO_NUMERIC(a)) = 1")

        sql = translate("SELECT some FROM table WHERE ISNUMERIC(a) = 0", "snowflake")
        assert_sql_equal(sql, "SELECT some FROM table WHERE IS_REAL(TRY_TO_NUMERIC(a)) = 0")

    def test_ceiling(self):
        sql = translate("SELECT CEILING(0.1);", "snowflake")
        assert_sql_equal(sql, "SELECT CEIL(0.1);")

    def test_top(self):
        sql = translate("SELECT TOP 10 * FROM my_table WHERE a = b;", "snowflake")
        assert_sql_equal(sql, "SELECT  * FROM my_table WHERE a = b LIMIT 10;")

    def test_drvd(self):
        sql = translate(
            "SELECT\n      TRY_CAST(name AS VARCHAR(MAX)) AS name,\n      TRY_CAST(speed AS FLOAT) AS speed\n    FROM (  VALUES ('A', 1.0), ('B', 2.0)) AS drvd(name, speed);",
            "snowflake",
        )
        assert_sql_equal(
            sql,
            "SELECT\n      CAST(name AS TEXT) AS name,\n      CAST(speed AS FLOAT) AS speed\n    FROM (VALUES ('A', 1.0), ('B', 2.0)) AS values_table (name, speed);",
        )

    def test_three_dots(self):
        sql = translate("SELECT x FROM my_table...1;", "snowflake")
        assert_sql_equal(sql, "SELECT x FROM my_tablexxx1;")

    def test_ab_three_dots(self):
        sql = translate("SELECT x FROM a.my_table...1;", "snowflake")
        assert_sql_equal(sql, "SELECT x FROM axmy_tablexxx1;")

    def test_abc_three_dots(self):
        sql = translate("SELECT x FROM a.b.my_table...1;", "snowflake")
        assert_sql_equal(sql, "SELECT x FROM axbxmy_tablexxx1;")

    def test_abc_three_dots_in_paren(self):
        sql = translate("(SELECT x FROM a.b.my_table...1)", "snowflake")
        assert_sql_equal(sql, "(SELECT x FROM axbxmy_tablexxx1)")

    def test_bitwise_and(self):
        sql = translate("SELECT ((a+b) & c/123) FROM table;", "snowflake")
        assert_sql_equal(sql, "SELECT BITAND((a+b) , c/123) FROM table ;")

    def test_cast_as_date(self):
        sql = translate("CAST('20000101' AS DATE);", "snowflake")
        assert_sql_equal(sql, "TO_DATE('20000101', 'YYYYMMDD');")
