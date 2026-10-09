"""Test HIVE translation - ported from OHDSI SqlRender test-translate-hive.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestHiveTranslation:
    def test_datediff_month(self):
        sql = translate(
            "SELECT DATEDIFF(Month,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "hive",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(MONTHS_BETWEEN(CAST(drug_era_end_date AS TIMESTAMP ), CAST(drug_era_start_date AS TIMESTAMP )) AS INT) FROM drug_era;",
        )

    def test_clustered_index_not_supported(self):
        sql = translate(
            "CREATE CLUSTERED INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "hive",
        )
        assert_sql_equal(sql, "-- hive does not support indexes")

    def test_index_not_supported(self):
        sql = translate(
            "CREATE INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "hive",
        )
        assert_sql_equal(sql, "-- hive does not support indexes")

    def test_index_with_where_not_supported(self):
        sql = translate(
            "CREATE INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date) WHERE cohort_definition_id=1;",
            "hive",
        )
        assert_sql_equal(sql, "-- hive does not support indexes")

    def test_charindex_from_position(self):
        sql = translate("SELECT CHARINDEX('test','abctest') FROM table", "hive")
        assert_sql_equal(sql, "SELECT INSTR('abctest','test') FROM table")

    def test_count(self):
        sql = translate("SELECT COUNT_BIG('test') FROM table", "hive")
        assert_sql_equal(sql, "SELECT COUNT('test') FROM table")

    def test_left_substr(self):
        sql = translate("SELECT LEFT('test',3)", "hive")
        assert_sql_equal(sql, "SELECT SUBSTR('test',1,3)")

    def test_right_substr(self):
        sql = translate("SELECT RIGHT('test',3)", "hive")
        assert_sql_equal(sql, "SELECT SUBSTR('test',-3)")

    def test_length(self):
        sql = translate("SELECT LEN('test')", "hive")
        assert_sql_equal(sql, "SELECT LENGTH('test')")

    def test_ln(self):
        sql = translate("SELECT LOG(10)", "hive")
        assert_sql_equal(sql, "SELECT LN(10)")

    def test_new_id(self):
        sql = translate("SELECT NEWID()", "hive")
        assert_sql_equal(sql, "SELECT reflect('java.util.UUID','randomUUID')")

    def test_round(self):
        sql = translate("SELECT ROUND('100.2564', 2)", "hive")
        assert_sql_equal(sql, "SELECT ROUND(CAST('100.2564' AS DOUBLE),2)")

    def test_square(self):
        sql = translate("SELECT SQUARE(2)", "hive")
        assert_sql_equal(sql, "SELECT ((2)*(2))")

    def test_stddev(self):
        sql = translate("SELECT STDEV(4)", "hive")
        assert_sql_equal(sql, "SELECT STDDEV_POP(4)")

    def test_variance(self):
        sql = translate("SELECT VAR(4)", "hive")
        assert_sql_equal(sql, "SELECT VARIANCE(4)")

    def test_date_add_day(self):
        sql = translate(
            "SELECT DATEADD(d,30,CAST(drug_era_end_date AS DATE)) FROM drug_era;",
            "hive",
        )
        assert_sql_equal(
            sql,
            "SELECT DATE_ADD(drug_era_end_date, 30) FROM drug_era;",
        )

    def test_date_add_month(self):
        sql = translate(
            "SELECT DATEADD(month,3,CAST(drug_era_end_date AS DATE)) FROM drug_era;",
            "hive",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(ADD_MONTHS(drug_era_end_date, 3) AS TIMESTAMP) FROM drug_era;",
        )

    def test_datefromparts(self):
        sql = translate("SELECT DATEFROMPARTS(1999,12,12);", "hive")
        assert_sql_equal(
            sql,
            "SELECT CAST(CONCAT(CAST(1999 AS STRING),'-',CAST(12 AS STRING),'-',CAST(12 AS STRING)) AS TIMESTAMP);",
        )

    def test_eomonth(self):
        sql = translate("SELECT eomonth(drug_era_end_date);", "hive")
        assert_sql_equal(sql, "SELECT CAST(last_day(drug_era_end_date) AS TIMESTAMP);")

    def test_timestamp(self):
        sql = translate("SELECT GETDATE();", "hive")
        assert_sql_equal(sql, "SELECT unix_timestamp();")

    def test_year_timestamp(self):
        sql = translate("SELECT year(unix_timestamp());", "hive")
        assert_sql_equal(sql, "SELECT year(from_unixtime(unix_timestamp()));")

    def test_create_table(self):
        sql = translate(
            "IF OBJECT_ID('test.testing', 'U') IS NULL CREATE TABLE test.testing (id int);",
            "hive",
        )
        assert_sql_equal(sql, "CREATE TABLE IF NOT EXISTS test.testing (id int);")

    def test_drop_table(self):
        sql = translate(
            "IF OBJECT_ID('test.testing', 'U') IS NOT NULL DROP TABLE test.testing;",
            "hive",
        )
        assert_sql_equal(sql, "DROP TABLE IF EXISTS test.testing;")

    def test_union(self):
        sql = translate("(SELECT test UNION SELECT ytest) ORDER BY", "hive")
        assert_sql_equal(
            sql,
            "SELECT * FROM\n(SELECT test\nUNION\nSELECT ytest)\nAS t1 ORDER BY",
        )

    def test_partition_if_not_exists(self):
        sql = (
            "HINT PARTITION(cohort_definition_id)\n"
            "IF OBJECT_ID('@results_schema.heracles_results_dist', 'U') IS NULL\n"
            "CREATE TABLE heracles_results_dist\n"
            "(\n"
            "cohort_definition_id int,\n"
            "analysis_id int,\n"
            "stratum_1 varchar(255),\n"
            ");"
        )
        sql_result = translate(sql, "hive")
        assert_sql_equal(
            sql_result,
            "partitioned table\n"
            "CREATE TABLE IF NOT EXISTS heracles_results_dist\n"
            "(   analysis_id int,\n"
            "stratum_1 varchar(255),\n"
            ")\n"
            "PARTITIONED BY(cohort_definition_id);",
        )

    def test_partition(self):
        sql = (
            "HINT PARTITION(cohort_definition_id)\n"
            "CREATE TABLE heracles_results_dist\n"
            "(\n"
            "cohort_definition_id int,\n"
            "analysis_id int,\n"
            "stratum_1 varchar(255),\n"
            ");"
        )
        sql_result = translate(sql, "hive")
        assert_sql_equal(
            sql_result,
            "partitioned table\n"
            "CREATE TABLE heracles_results_dist\n"
            "(   analysis_id int,\n"
            "stratum_1 varchar(255),\n"
            ")\n"
            "PARTITIONED BY(cohort_definition_id);",
        )

    def test_bucket_if_not_exists(self):
        sql = (
            "HINT BUCKET(analysis_id, 64)\n"
            "IF OBJECT_ID('@results_schema.heracles_results_dist', 'U') IS NULL\n"
            "CREATE TABLE heracles_results_dist\n"
            "(\n"
            "cohort_definition_id int,\n"
            "analysis_id int,\n"
            "stratum_1 varchar(255),\n"
            ");"
        )
        sql_result = translate(sql, "hive")
        assert_sql_equal(
            sql_result,
            "table with bucket\n"
            "CREATE TABLE IF NOT EXISTS heracles_results_dist\n"
            "(cohort_definition_id int,\n"
            "analysis_id int,\n"
            "stratum_1 varchar(255),\n"
            ")\n"
            "CLUSTERED by(analysis_id) into 64 BUCKETS;",
        )

    def test_bucket(self):
        sql = (
            "HINT BUCKET(analysis_id, 64)\n"
            "CREATE TABLE heracles_results_dist\n"
            "(\n"
            "cohort_definition_id int,\n"
            "analysis_id int,\n"
            "stratum_1 varchar(255),\n"
            ");"
        )
        sql_result = translate(sql, "hive")
        assert_sql_equal(
            sql_result,
            "table with bucket\n"
            "CREATE TABLE heracles_results_dist\n"
            "(cohort_definition_id int,\n"
            "analysis_id int,\n"
            "stratum_1 varchar(255),\n"
            ")\n"
            "CLUSTERED by(analysis_id) into 64 BUCKETS;",
        )

    def test_dbo(self):
        sql = translate(".dbo.", "hive")
        assert_sql_equal(sql, ".")

    def test_top_in_subqueries(self):
        sql = translate(
            "select statistic_value from achilles_results join (SELECT TOP 1 count as total_pts from achilles_results where analysis_id = 1) where analysis_id in (2002,2003)",
            "hive",
        )
        assert_sql_equal(
            sql,
            "select statistic_value from achilles_results join (SELECT count as total_pts from achilles_results where analysis_id = 1 LIMIT 1) where analysis_id in (2002,2003)",
        )

    def test_top_in_subqueries_with_parentheses(self):
        sql = translate(
            "(select statistic_value from achilles_results join (SELECT TOP 1 count as total_pts from achilles_results where analysis_id = 1) where analysis_id in (2002,2003))",
            "hive",
        )
        assert_sql_equal(
            sql,
            "(select statistic_value from achilles_results join (SELECT count as total_pts from achilles_results where analysis_id = 1 LIMIT 1) where analysis_id in (2002,2003))",
        )

    def test_date(self):
        sql = translate("DATE", "hive")
        assert_sql_equal(sql, "TIMESTAMP")

    def test_datetime(self):
        sql = translate("DATETIME", "hive")
        assert_sql_equal(sql, "TIMESTAMP")

    def test_datetime2(self):
        sql = translate("DATETIME2", "hive")
        assert_sql_equal(sql, "TIMESTAMP")

    def test_bigint_not_null(self):
        sql = translate("BIGINT NOT NULL", "hive")
        assert_sql_equal(sql, "BIGINT")

    def test_boolean_not_null(self):
        sql = translate("BOOLEAN NOT NULL", "hive")
        assert_sql_equal(sql, "BOOLEAN")

    def test_char_not_null(self):
        sql = translate("CHAR NOT NULL", "hive")
        assert_sql_equal(sql, "CHAR")

    def test_decimal_not_null(self):
        sql = translate("DECIMAL NOT NULL", "hive")
        assert_sql_equal(sql, "DECIMAL")

    def test_double_not_null(self):
        sql = translate("DOUBLE NOT NULL", "hive")
        assert_sql_equal(sql, "DOUBLE")

    def test_float_not_null(self):
        sql = translate("FLOAT NOT NULL", "hive")
        assert_sql_equal(sql, "FLOAT")

    def test_int_not_null(self):
        sql = translate("INT NOT NULL", "hive")
        assert_sql_equal(sql, "INT")

    def test_real_not_null(self):
        sql = translate("REAL NOT NULL", "hive")
        assert_sql_equal(sql, "FLOAT")

    def test_smallint_not_null(self):
        sql = translate("SMALLINT NOT NULL", "hive")
        assert_sql_equal(sql, "SMALLINT")

    def test_string_not_null(self):
        sql = translate("STRING NOT NULL", "hive")
        assert_sql_equal(sql, "VARCHAR")

    def test_timestamp_not_null(self):
        sql = translate("TIMESTAMP NOT NULL", "hive")
        assert_sql_equal(sql, "TIMESTAMP")

    def test_tinyint_not_null(self):
        sql = translate("TINYINT NOT NULL", "hive")
        assert_sql_equal(sql, "TINYINT")

    def test_varchar_not_null(self):
        sql = translate("VARCHAR(10) NOT NULL", "hive")
        assert_sql_equal(sql, "VARCHAR(10)")

    def test_bigint_null(self):
        sql = translate("BIGINT NULL", "hive")
        assert_sql_equal(sql, "BIGINT")

    def test_boolean_null(self):
        sql = translate("BOOLEAN NULL", "hive")
        assert_sql_equal(sql, "BOOLEAN")

    def test_char_null(self):
        sql = translate("CHAR NULL", "hive")
        assert_sql_equal(sql, "CHAR")

    def test_decimal_null(self):
        sql = translate("DECIMAL NULL", "hive")
        assert_sql_equal(sql, "DECIMAL")

    def test_double_null(self):
        sql = translate("DOUBLE NULL", "hive")
        assert_sql_equal(sql, "DOUBLE")

    def test_float_null(self):
        sql = translate("FLOAT NULL", "hive")
        assert_sql_equal(sql, "FLOAT")

    def test_int_null(self):
        sql = translate("INT NULL", "hive")
        assert_sql_equal(sql, "INT")

    def test_real_null(self):
        sql = translate("FLOAT NULL", "hive")
        assert_sql_equal(sql, "FLOAT")

    def test_smallint_null(self):
        sql = translate("SMALLINT NULL", "hive")
        assert_sql_equal(sql, "SMALLINT")

    def test_string_null(self):
        sql = translate("STRING NULL", "hive")
        assert_sql_equal(sql, "VARCHAR")

    def test_timestamp_null(self):
        sql = translate("TIMESTAMP NULL", "hive")
        assert_sql_equal(sql, "TIMESTAMP")

    def test_tinyint_null(self):
        sql = translate("TINYINT NULL", "hive")
        assert_sql_equal(sql, "TINYINT")

    def test_varchar_null(self):
        sql = translate("VARCHAR(10) NULL", "hive")
        assert_sql_equal(sql, "VARCHAR(10)")

    def test_char(self):
        sql = translate("CHAR,", "hive")
        assert_sql_equal(sql, "CHAR(1),")

    def test_char_newline(self):
        sql = translate("CHAR\n+", "hive")
        assert_sql_equal(sql, "CHAR(1)\n")

    def test_char_rparen(self):
        sql = translate("CHAR)", "hive")
        assert_sql_equal(sql, "CHAR(1))")

    def test_constraint_default_timestamp(self):
        sql = translate("CONSTRAINT test DEFAULT unix_timestamp()", "hive")
        assert_sql_equal(sql, "")

    def test_default_timestamp(self):
        sql = translate("DEFAULT unix_timestamp()", "hive")
        assert_sql_equal(sql, "")

    def test_update_statistics(self):
        sql = translate("UPDATE STATISTICS results_schema.heracles_results;", "hive")
        assert_sql_equal(sql, "-- hive does not support COMPUTE STATS")

    def test_cast_varchar(self):
        sql = translate("CAST(10 AS VARCHAR)", "hive")
        assert_sql_equal(sql, "CAST(10 AS VARCHAR(1000))")

    def test_coalesce(self):
        sql = translate("ISNULL(abc,gde)", "hive")
        assert_sql_equal(sql, "COALESCE(abc,gde)")

    def test_with_as_temp(self):
        sql = (
            "WITH cteRawData as (select coh_id FROM #raw_706),\n"
            "overallStats as (select coh_id from cteRawData),\n"
            "valueStats as (select total FROM (select coh_id FROM cteRawData GROUP BY coh_id) D)\n"
            "select o.coh_id, 706 as analysis_id into #results_dist_706 from valueStats s\n"
            "join overallStats o on s.coh_id = o.coh_id;"
        )
        sql_result = translate(sql, "hive")
        assert_sql_equal(
            sql_result,
            "DROP TABLE IF EXISTS cteRawData; DROP TABLE IF EXISTS overallStats; DROP TABLE IF EXISTS valueStats;\n"
            "CREATE TEMPORARY TABLE cteRawData AS select coh_id FROM raw_706;\n"
            "CREATE TEMPORARY TABLE overallStats AS select coh_id from cteRawData;\n"
            "CREATE TEMPORARY TABLE valueStats AS select total FROM (select coh_id FROM cteRawData GROUP BY coh_id) D;\n"
            "CREATE TEMPORARY TABLE results_dist_706 AS SELECT o.coh_id, 706 as analysis_id FROM valueStats s\n"
            "join overallStats o on s.coh_id = o.coh_id;",
        )

    def test_temp_table(self):
        sql = translate("select coh_id into #raw_706 from cteRawData;", "hive")
        assert_sql_equal(
            sql,
            "CREATE TEMPORARY TABLE IF NOT EXISTS raw_706 AS\nSELECT\ncoh_id\nFROM\ncteRawData;",
        )

    def test_temp_table_without_from(self):
        sql = translate("select coh_id into #raw_706;", "hive")
        assert_sql_equal(
            sql,
            "CREATE TEMPORARY TABLE IF NOT EXISTS raw_706 AS\nSELECT\ncoh_id;",
        )

    def test_temp_table_if_not_exists(self):
        sql = translate("CREATE TABLE #raw_706 (coh_id int)", "hive")
        assert_sql_equal(
            sql,
            "CREATE TEMPORARY TABLE IF NOT EXISTS raw_706 (coh_id int)",
        )

    def test_several_temp_table(self):
        sql = translate(
            "CREATE TEMPORARY TABLE raw_707 as (select coh_id FROM #raw_706), overallStats (coh_id) as (select coh_id from cteRawData)\n;",
            "hive",
        )
        assert_sql_equal(
            sql,
            "DROP TABLE IF EXISTS raw_707; DROP TABLE IF EXISTS overallStats; CREATE TEMPORARY TABLE raw_707 AS (select coh_id FROM raw_706)\n"
            ";\n"
            "CREATE TEMPORARY TABLE overallStats AS (select coh_id from cteRawData)\n"
            ";",
        )

    def test_several_temp_table_without_definitions(self):
        sql = translate(
            "CREATE TEMPORARY TABLE raw_707 as (select coh_id FROM #raw_706), overallStats as (select coh_id from cteRawData)\n;",
            "hive",
        )
        assert_sql_equal(
            sql,
            "DROP TABLE IF EXISTS raw_707; DROP TABLE IF EXISTS overallStats; CREATE TEMPORARY TABLE raw_707 AS (select coh_id FROM raw_706)\n"
            ";\n"
            "CREATE TEMPORARY TABLE overallStats AS (select coh_id from cteRawData)\n"
            ";",
        )

    def test_drop_with_definition(self):
        sql = translate("DROP TABLE IF EXISTS test.testing (id int)", "hive")
        assert_sql_equal(sql, "DROP TABLE IF EXISTS test.testing ")

    def test_subquery(self):
        sql = translate(
            "SELECT o.coh_id, 706 as analysis_id into results_dist_706 from valueStats;",
            "hive",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE IF NOT EXISTS results_dist_706 AS\n"
            "SELECT\n"
            "o.coh_id, 706 as analysis_id\n"
            "FROM\n"
            "valueStats;",
        )

    def test_distinct(self):
        sql = translate(
            "SELECT o.coh_id, 706 as analysis_id into results_dist_706 from valueStats;",
            "hive",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE IF NOT EXISTS results_dist_706 AS\n"
            "SELECT\n"
            "o.coh_id, 706 as analysis_id\n"
            "FROM\n"
            "valueStats;",
        )

    def test_intersect_distinct(self):
        sql = translate(
            "SELECT DISTINCT a FROM t INTERSECT SELECT DISTINCT a FROM s;",
            "hive",
        )
        assert_sql_equal(
            sql,
            "SELECT t1.a FROM (SELECT DISTINCT a FROM t UNION ALL SELECT DISTINCT a FROM s) AS t1 GROUP BY a HAVING COUNT(*) >= 2;",
        )

    def test_bracketed_intersect_distinct(self):
        sql = translate(
            "(SELECT DISTINCT a FROM t INTERSECT SELECT DISTINCT a FROM s)",
            "hive",
        )
        assert_sql_equal(
            sql,
            "(SELECT t1.a FROM (SELECT DISTINCT a FROM t UNION ALL SELECT DISTINCT a FROM s) AS t1 GROUP BY a HAVING COUNT(*) >= 2)",
        )

    def test_dash(self):
        sql = translate("#", "hive")
        assert_sql_equal(sql, "")

    def test_extra_space(self):
        sql = translate(
            "(coh_id int, analysis_id int)  AS select o.coh_id, 706 as analysis_id FROM valueStats s",
            "hive",
        )
        assert_sql_equal(
            sql,
            "(coh_id int, analysis_id int) AS select o.coh_id, 706 as analysis_id FROM valueStats s",
        )

    def test_table_without_definition(self):
        sql = translate(
            "CREATE TABLE cteRawData (coh_id int) AS select coh_id FROM raw_706",
            "hive",
        )
        assert_sql_equal(sql, "CREATE TABLE cteRawData AS select coh_id FROM raw_706")

    def test_digits(self):
        sql = translate("WHEN .123456 * ", "hive")
        assert_sql_equal(sql, "WHEN 0.123456 * ")

    def test_digits2(self):
        sql = translate("WHEN .123456 * ", "hive")
        assert_sql_equal(sql, "WHEN 0.123456 * ")

    def test_isnumeric(self):
        sql = translate("select ISNUMERIC(a) from b", "hive")
        assert_sql_equal(
            sql,
            "select case when cast(a as double) is not null then 1 else 0 end from b",
        )

    def test_as(self):
        sql = translate('as "test_variable"', "hive")
        assert_sql_equal(sql, "as test_variable")

    def test_hashbytes(self):
        sql = translate(
            "SELECT AVG(CAST(CAST(CONVERT(VARBINARY, HASHBYTES('MD5',line), 1) AS INT) AS BIGINT)) as checksum",
            "hive",
        )
        assert_sql_equal(
            sql,
            "SELECT AVG(CAST(CAST(hash(line) AS INT) AS BIGINT)) as checksum",
        )
