"""Test Impala translation - ported from OHDSI SqlRender test-translate-impala.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestImpalaTranslation:
    def test_select_random_row_using_hash(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY HASHBYTES('MD5',CAST(person_id AS varchar))) tmp WHERE rn <= 1",
            "impala",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY fnv_hash(CAST(person_id AS varchar))) tmp WHERE rn <= 1",
        )

    def test_select_convert_varbinary(self):
        sql = translate(
            "SELECT ROW_NUMBER() OVER CONVERT(VARBINARY, val, 1) rn WHERE rn <= 1",
            "impala",
        )
        assert_sql_equal(
            sql,
            "SELECT ROW_NUMBER() OVER cast(conv(val, 16, 10) as int) rn WHERE rn <= 1",
        )

    def test_clustered_index_not_supported(self):
        sql = translate(
            "CREATE CLUSTERED INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "impala",
        )
        assert_sql_equal(sql, "-- impala does not support indexes")

    def test_index_not_supported(self):
        sql = translate(
            "CREATE INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "impala",
        )
        assert_sql_equal(sql, "-- impala does not support indexes")

    def test_use(self):
        sql = translate("USE vocabulary;", "impala")
        assert_sql_equal(sql, "USE vocabulary;")

    def test_cast_as_date(self):
        sql = translate("CAST('20000101' AS DATE);", "impala")
        assert_sql_equal(
            sql,
            "CASE TYPEOF('20000101' ) WHEN 'TIMESTAMP' THEN CAST('20000101'  AS TIMESTAMP) ELSE TO_UTC_TIMESTAMP(CONCAT_WS('-', SUBSTR(CAST('20000101'  AS STRING), 1, 4), SUBSTR(CAST('20000101'  AS STRING), 5, 2), SUBSTR(CAST('20000101'  AS STRING), 7, 2)), 'UTC') END;",
        )

    def test_datediff(self):
        sql = translate(
            "SELECT DATEDIFF(dd,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "impala",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(CASE TYPEOF(drug_era_end_date ) WHEN 'TIMESTAMP' THEN CAST(drug_era_end_date  AS TIMESTAMP) ELSE TO_UTC_TIMESTAMP(CONCAT_WS('-', SUBSTR(CAST(drug_era_end_date  AS STRING), 1, 4), SUBSTR(CAST(drug_era_end_date  AS STRING), 5, 2), SUBSTR(CAST(drug_era_end_date  AS STRING), 7, 2)), 'UTC') END, CASE TYPEOF(drug_era_start_date ) WHEN 'TIMESTAMP' THEN CAST(drug_era_start_date  AS TIMESTAMP) ELSE TO_UTC_TIMESTAMP(CONCAT_WS('-', SUBSTR(CAST(drug_era_start_date  AS STRING), 1, 4), SUBSTR(CAST(drug_era_start_date  AS STRING), 5, 2), SUBSTR(CAST(drug_era_start_date  AS STRING), 7, 2)), 'UTC') END) FROM drug_era;",
        )

    def test_datediff_month(self):
        sql = translate(
            "SELECT DATEDIFF(month,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "impala",
        )
        assert_sql_equal(
            sql,
            "SELECT INT_MONTHS_BETWEEN(CASE TYPEOF(drug_era_end_date ) WHEN 'TIMESTAMP' THEN CAST(drug_era_end_date  AS TIMESTAMP) ELSE TO_UTC_TIMESTAMP(CONCAT_WS('-', SUBSTR(CAST(drug_era_end_date  AS STRING), 1, 4), SUBSTR(CAST(drug_era_end_date  AS STRING), 5, 2), SUBSTR(CAST(drug_era_end_date  AS STRING), 7, 2)), 'UTC') END, CASE TYPEOF(drug_era_start_date ) WHEN 'TIMESTAMP' THEN CAST(drug_era_start_date  AS TIMESTAMP) ELSE TO_UTC_TIMESTAMP(CONCAT_WS('-', SUBSTR(CAST(drug_era_start_date  AS STRING), 1, 4), SUBSTR(CAST(drug_era_start_date  AS STRING), 5, 2), SUBSTR(CAST(drug_era_start_date  AS STRING), 7, 2)), 'UTC') END) FROM drug_era;",
        )

    def test_dateadd(self):
        sql = translate(
            "SELECT DATEADD(dd,30,drug_era_end_date) FROM drug_era;",
            "impala",
        )
        assert_sql_equal(
            sql,
            "SELECT DATE_ADD(CASE TYPEOF(drug_era_end_date ) WHEN 'TIMESTAMP' THEN CAST(drug_era_end_date  AS TIMESTAMP) ELSE TO_UTC_TIMESTAMP(CONCAT_WS('-', SUBSTR(CAST(drug_era_end_date  AS STRING), 1, 4), SUBSTR(CAST(drug_era_end_date  AS STRING), 5, 2), SUBSTR(CAST(drug_era_end_date  AS STRING), 7, 2)), 'UTC') END, 30) FROM drug_era;",
        )

    def test_with_select(self):
        sql = translate("WITH cte1 AS (SELECT a FROM b) SELECT c FROM cte1;", "impala")
        assert_sql_equal(sql, "WITH cte1 AS (SELECT a FROM b) SELECT c FROM cte1;")

    def test_with_select_into(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "impala",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE d STORED AS PARQUET \nAS\nWITH cte1 AS (SELECT a FROM b) SELECT\n c \nFROM\n cte1;\n COMPUTE STATS d;",
        )

    def test_select_into_without_from(self):
        sql = translate("SELECT c INTO d;", "impala")
        assert_sql_equal(
            sql,
            "CREATE TABLE d STORED AS PARQUET AS\nSELECT\n c;\n COMPUTE STATS d;",
        )

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NULL\n CREATE TABLE cohort\n(cohort_definition_id INT);",
            "impala",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE IF NOT EXISTS cohort\n (cohort_definition_id INT);",
        )

    def test_drop_table_if_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NOT NULL DROP TABLE cohort;",
            "impala",
        )
        assert_sql_equal(sql, "DROP TABLE IF EXISTS cohort;")

    def test_union_order_by(self):
        sql = translate("(SELECT a FROM b UNION SELECT a FROM c) ORDER BY a", "impala")
        assert_sql_equal(
            sql,
            "SELECT * FROM \n ( SELECT a FROM b \n UNION \n SELECT a FROM c ) \n AS t1 ORDER BY a",
        )

    def test_right_functions(self):
        sql = translate("SELECT RIGHT(x,4);", "impala")
        assert_sql_equal(sql, "SELECT SUBSTR(x,-4);")

    def test_delete_from(self):
        sql = translate("delete from ACHILLES_results;", "impala")
        assert_sql_equal(sql, "TRUNCATE TABLE ACHILLES_results;")

    def test_delete_from_where(self):
        sql = translate(
            "delete from ACHILLES_results where analysis_id IN (1, 2, 3);",
            "impala",
        )
        assert_sql_equal(
            sql,
            "INSERT OVERWRITE TABLE ACHILLES_results SELECT * FROM ACHILLES_results WHERE NOT(analysis_id IN (1, 2, 3));",
        )

    def test_location_reserved_word(self):
        sql = translate("select count(1) from omop_cdm.location;", "impala")
        assert_sql_equal(sql, "select count(1) from omop_cdm.`location`;")

    def test_top_in_subqueries(self):
        sql = translate(
            "select statistic_value from achilles_results join (SELECT TOP 1 count as total_pts from achilles_results where analysis_id = 1) where analysis_id in (2002,2003)",
            "impala",
        )
        assert_sql_equal(
            sql,
            "select statistic_value from achilles_results join (SELECT count as total_pts from achilles_results where analysis_id = 1 LIMIT 1) where analysis_id in (2002,2003)",
        )

    def test_create_table_with_not_null(self):
        sql = translate(
            "CREATE TABLE a (c1 BIGINT NOT NULL, c2 BOOLEAN NOT NULL, c3 CHAR NOT NULL, c4 DECIMAL NOT NULL, c5 DOUBLE NOT NULL, c6 FLOAT NOT NULL, c7 INT NOT NULL, c8 REAL NOT NULL, c9 SMALLINT NOT NULL, c10 STRING NOT NULL, c11 TIMESTAMP NOT NULL, c12 TINYINT NOT NULL, c13 VARCHAR(10) NOT NULL, c14 DATE NOT NULL, c15 DATETIME NOT NULL, c16 INTEGER NOT NULL)",
            "impala",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE a (c1 BIGINT, c2 BOOLEAN, c3 CHAR(1), c4 DECIMAL, c5 DOUBLE, c6 FLOAT, c7 INT, c8 REAL, c9 SMALLINT, c10 STRING, c11 TIMESTAMP, c12 TINYINT, c13 VARCHAR(10), c14 TIMESTAMP, c15 TIMESTAMP, c16 INT)",
        )

    def test_create_table_with_null(self):
        sql = translate(
            "CREATE TABLE a (c1 BIGINT NULL, c2 BOOLEAN NULL, c3 CHAR NULL, c4 DECIMAL NULL, c5 DOUBLE NULL, c6 FLOAT NULL, c7 INT NULL, c8 REAL NULL, c9 SMALLINT NULL, c10 STRING NULL, c11 TIMESTAMP NULL, c12 TINYINT NULL, c13 VARCHAR(10) NULL, c14 DATE NULL, c15 DATETIME NULL)",
            "impala",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE a (c1 BIGINT, c2 BOOLEAN, c3 CHAR(1), c4 DECIMAL, c5 DOUBLE, c6 FLOAT, c7 INT, c8 REAL, c9 SMALLINT, c10 STRING, c11 TIMESTAMP, c12 TINYINT, c13 VARCHAR(10), c14 TIMESTAMP, c15 TIMESTAMP)",
        )

    def test_clause_with_not_null(self):
        sql = translate("SELECT * FROM x WHERE y IS NOT NULL", "impala")
        assert_sql_equal(sql, "SELECT * FROM x WHERE y IS NOT NULL")

    def test_create_table_with_constraint_default(self):
        sql = translate(
            "CREATE TABLE a(c1 TIMESTAMP CONSTRAINT a_c1_def DEFAULT NOW())",
            "impala",
        )
        assert_sql_equal(sql, "CREATE TABLE a(c1 TIMESTAMP)")

    def test_create_table_with_default(self):
        sql = translate("CREATE TABLE a(c1 TIMESTAMP DEFAULT NOW())", "impala")
        assert_sql_equal(sql, "CREATE TABLE a(c1 TIMESTAMP)")

    def test_stats_reserved_word(self):
        sql = translate("SELECT * FROM strata_stats AS stats", "impala")
        assert_sql_equal(sql, "SELECT * FROM strata_stats AS _stats")

    def test_datefromparts(self):
        sql = translate("SELECT DATEFROMPARTS('1977', '10', '12')", "impala")
        assert_sql_equal(
            sql,
            "SELECT to_timestamp(CONCAT(CAST('1977' AS VARCHAR),'-',CAST('10' AS VARCHAR),'-',CAST('12' AS VARCHAR)), 'yyyy-M-d')",
        )

    def test_eomonth(self):
        sql = translate(
            "SELECT eomonth(payer_plan_period_start_date) AS obs_month_end",
            "impala",
        )
        assert_sql_equal(
            sql,
            "SELECT days_sub(add_months(trunc(CAST(payer_plan_period_start_date AS TIMESTAMP), 'MM'),1),1) AS obs_month_end",
        )

    def test_isnumeric(self):
        sql = translate("SELECT ISNUMERIC(a) FROM b", "impala")
        assert_sql_equal(
            sql,
            "SELECT case when regexp_like(a,'^([0-9]+\\.?[0-9]*|\\.[0-9]+)$') then 1 else 0 end FROM b",
        )
        sql = translate("SELECT some FROM table WHERE ISNUMERIC(a) = 1", "impala")
        assert_sql_equal(
            sql,
            "SELECT some FROM table WHERE case when regexp_like(a,'^([0-9]+\\.?[0-9]*|\\.[0-9]+)$') then 1 else 0 end = 1",
        )
        sql = translate("SELECT some FROM table WHERE ISNUMERIC(a) = 0", "impala")
        assert_sql_equal(
            sql,
            "SELECT some FROM table WHERE case when regexp_like(a,'^([0-9]+\\.?[0-9]*|\\.[0-9]+)$') then 1 else 0 end = 0",
        )

    def test_data_types(self):
        sql = translate("CREATE TABLE a (c1 DOUBLE PRECISION)", "impala")
        assert_sql_equal(sql, "CREATE TABLE a (c1 DOUBLE)")

    def test_escape_chars(self):
        sql = translate(
            "INSERT INTO t VALUES('some \"string\" ''with escape'' chars')",
            "impala",
        )
        assert_sql_equal(
            sql,
            "INSERT INTO t VALUES(CONCAT('some \\042string\\042 ','\\047','with escape','\\047',' chars'))",
        )

    def test_top(self):
        sql = translate("SELECT TOP 10 * FROM my_table WHERE a = b;", "impala")
        assert_sql_equal(sql, "SELECT * FROM my_table WHERE a = b LIMIT 10;")

    def test_analyze_table(self):
        sql = translate("UPDATE STATISTICS results_schema.heracles_results;", "impala")
        assert_sql_equal(sql, "COMPUTE STATS results_schema.heracles_results;")

    def test_temp_table_field_ref(self):
        sql = translate(
            "SELECT #tmp.name FROM #tmp;",
            "impala",
            temp_emulation_schema="ts",
            session_id="T0000000",
        )
        assert_sql_equal(
            sql,
            "SELECT T0000000tmp.name FROM ts.T0000000tmp;",
        )
