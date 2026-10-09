"""Test Netezza translation - ported from OHDSI SqlRender test-translate-netezza.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestNetezzaTranslation:
    def test_select_random_row(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RAND()) AS rn FROM table) tmp WHERE rn <= 1",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn FROM table) tmp WHERE rn <= 1",
        )

    def test_select_random_row_using_hash(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY HASHBYTES('MD5',CAST(person_id AS varchar))) tmp WHERE rn <= 1",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY hash(CAST(person_id AS VARCHAR(1000)))) tmp WHERE rn <= 1",
        )

    def test_select_convert_varbinary(self):
        sql = translate(
            "SELECT ROW_NUMBER() OVER CONVERT(VARBINARY, val, 1) rn WHERE rn <= 1",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "SELECT ROW_NUMBER() OVER hex_to_binary(val) rn WHERE rn <= 1",
        )

    def test_with_cte_insert_into(self):
        sql = translate(
            "WITH data AS (SELECT 'test' AS user, 'secret' AS password) INSERT INTO users SELECT * FROM data;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "INSERT INTO users WITH data AS (SELECT 'test' AS user, 'secret' AS password) SELECT * FROM data;",
        )

    def test_cast_as_date(self):
        sql = translate("CAST('20000101' AS DATE);", "netezza")
        assert_sql_equal(sql, "TO_DATE('20000101' , 'yyyymmdd');")

    def test_datediff(self):
        sql = translate(
            "SELECT DATEDIFF(dd,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "SELECT (CAST(drug_era_end_date AS DATE) - CAST(drug_era_start_date AS DATE)) FROM drug_era;",
        )

    def test_datediff_year(self):
        sql = translate(
            "SELECT DATEDIFF(YEAR,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "SELECT (DATE_PART('YEAR', CAST(drug_era_end_date AS DATE)) - DATE_PART('YEAR', CAST(drug_era_start_date AS DATE))) FROM drug_era;",
        )

    def test_datediff_month(self):
        sql = translate(
            "SELECT DATEDIFF(month,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "SELECT MONTHS_BETWEEN(CAST(drug_era_end_date AS DATE), CAST(drug_era_start_date AS DATE)) FROM drug_era;",
        )

    def test_dateadd(self):
        sql = translate(
            "SELECT DATEADD(dd,30,drug_era_end_date) FROM drug_era;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "SELECT (drug_era_end_date + 30) FROM drug_era;",
        )

    def test_with_select(self):
        sql = translate("WITH cte1 AS (SELECT a FROM b) SELECT c FROM cte1;", "netezza")
        assert_sql_equal(sql, "WITH cte1 AS (SELECT a FROM b) SELECT c FROM cte1;")

    def test_with_select_into(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE d \nAS\nWITH cte1  AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1;",
        )

    def test_with_cte_select_into_with_random_distribution(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_RANDOM\nWITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_RANDOM\nCREATE TABLE d \nAS\nWITH cte1  AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1\nDISTRIBUTE ON RANDOM;",
        )

    def test_with_cte_select_into_with_key_distribution(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(c)\nWITH cte1 AS (SELECT a,c FROM b) SELECT c INTO d FROM cte1;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(c)\nCREATE TABLE d \nAS\nWITH cte1  AS (SELECT a,c FROM b)  SELECT\nc \nFROM\ncte1\nDISTRIBUTE ON (c);",
        )

    def test_with_select_into_with_random_distribution(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_RANDOM\nSELECT a INTO b FROM someTable;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_RANDOM\nCREATE TABLE b \nAS\nSELECT\na \nFROM\nsomeTable\nDISTRIBUTE ON RANDOM;",
        )

    def test_with_select_into_with_key_distribution(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(a)\nSELECT a INTO b FROM someTable;",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(a)\nCREATE TABLE b \nAS\nSELECT\na \nFROM\nsomeTable\nDISTRIBUTE ON (a);",
        )

    def test_select_into_temp_table(self):
        sql = translate("SELECT a INTO #b;", "netezza")
        assert_sql_equal(sql, "CREATE TEMP TABLE b\n AS \n SELECT \n a;")

    def test_select_into_table(self):
        sql = translate("SELECT a INTO b;", "netezza")
        assert_sql_equal(sql, "CREATE TABLE b \n AS \n SELECT a;")

    def test_drop_table_if_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NOT NULL DROP TABLE cohort;",
            "netezza",
        )
        assert_sql_equal(sql, "DROP TABLE cohort IF EXISTS;")

    def test_left_functions(self):
        sql = translate("SELECT LEFT(x,4);", "netezza")
        assert_sql_equal(sql, "SELECT SUBSTR(x, 1, 4);")

    def test_right_functions(self):
        sql = translate("SELECT RIGHT(x,4);", "netezza")
        assert_sql_equal(sql, "SELECT SUBSTR(x, LENGTH(x) - 4 + 1, 4);")

    def test_delete_from_where(self):
        sql = translate(
            "delete from ACHILLES_results where analysis_id IN (1, 2, 3);",
            "netezza",
        )
        assert_sql_equal(
            sql,
            "delete from ACHILLES_results where analysis_id IN (1, 2, 3);",
        )

    def test_cast_as_varchar(self):
        sql = translate("CAST(person_id AS VARCHAR);", "netezza")
        assert_sql_equal(sql, "CAST(person_id AS VARCHAR(1000));")

    def test_top(self):
        sql = translate("SELECT TOP 10 * FROM my_table WHERE a = b;", "netezza")
        assert_sql_equal(sql, "SELECT * FROM my_table WHERE a = b LIMIT 10;")

    def test_top_subquery(self):
        sql = translate(
            "SELECT * FROM (SELECT TOP 10 * FROM my_table WHERE a = b);",
            "netezza",
        )
        assert_sql_equal(sql, "SELECT * FROM (SELECT * FROM my_table WHERE a = b LIMIT 10);")

    def test_isnumeric(self):
        sql = translate("SELECT ISNUMERIC(a) FROM b", "netezza")
        assert_sql_equal(
            sql,
            "SELECT CASE WHEN translate(a,'0123456789','') in ('','.','-','-.') THEN 1 ELSE 0 END FROM b",
        )
        sql = translate("SELECT some FROM table WHERE ISNUMERIC(a) = 1", "netezza")
        assert_sql_equal(
            sql,
            "SELECT some FROM table WHERE CASE WHEN translate(a,'0123456789','') in ('','.','-','-.') THEN 1 ELSE 0 END = 1",
        )
        sql = translate("SELECT some FROM table WHERE ISNUMERIC(a) = 0", "netezza")
        assert_sql_equal(
            sql,
            "SELECT some FROM table WHERE CASE WHEN translate(a,'0123456789','') in ('','.','-','-.') THEN 1 ELSE 0 END = 0",
        )

    def test_concat_with_more_than_two_arguments(self):
        sql = translate("SELECT CONCAT(a,b,c,d,e) FROM x;", "netezza")
        assert_sql_equal(sql, "SELECT a || b || c || d || e FROM x;")

    def test_nested_concat(self):
        sql = translate(
            "SELECT CONCAT(CONCAT(CONCAT(a,CONCAT(b,c)),d),e) FROM x;",
            "netezza",
        )
        assert_sql_equal(sql, "SELECT a || b || c || d || e FROM x;")

    def test_clustered_index_not_supported(self):
        sql = translate(
            "CREATE CLUSTERED INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "netezza",
        )
        assert_sql_equal(sql, "-- netezza does not support indexes")

    def test_index_not_supported(self):
        sql = translate(
            "CREATE INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "netezza",
        )
        assert_sql_equal(sql, "-- netezza does not support indexes")

    def test_analyze_table(self):
        sql = translate("UPDATE STATISTICS results_schema.heracles_results;", "netezza")
        assert_sql_equal(sql, "GENERATE STATISTICS ON results_schema.heracles_results;")

    def test_drop_table_if_exists_direct(self):
        sql = translate("DROP TABLE IF EXISTS test;", "netezza")
        assert_sql_equal(sql, "DROP TABLE test IF EXISTS;")

    def test_drop_table_if_exists_temp(self):
        sql = translate("DROP TABLE IF EXISTS #my_temp;", "netezza")
        assert_sql_equal(sql, "DROP TABLE my_temp IF EXISTS;")
