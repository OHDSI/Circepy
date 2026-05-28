"""Test PostgreSQL translation - ported from OHDSI SqlRender test-translate-postgresql.R"""

import re

from circe.sqlrender import translate


def setup_function():
    global _target_to_patterns
    _target_to_patterns = None


def normalize_sql(s: str) -> str:
    s = re.sub(r"([;()'+\-/|*\n])", r" \1 ", s)
    s = re.sub(r" +", " ", s)
    return s.strip()


def assert_sql_equal(actual: str, expected: str):
    assert normalize_sql(actual) == normalize_sql(expected), f"\nExpected: {expected}\nGot:      {actual}"


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
            " CAST(drug_era_start_date AS DATE)))*12"
            " + extract(month from age(CAST(drug_era_end_date AS DATE),"
            " CAST(drug_era_start_date AS DATE)))) FROM drug_era;"
        )
        assert_sql_equal(sql, expected)

    def test_datediff_hour(self):
        sql = translate(
            "SELECT DATEDIFF(hour,drug_exposure_start_datetime,drug_exposure_end_datetime) FROM drug_exposure;",
            "postgresql",
        )
        expected = (
            "SELECT (EXTRACT(EPOCH FROM (drug_exposure_end_datetime"
            " - drug_exposure_start_datetime)) / 3600) FROM drug_exposure;"
        )
        assert_sql_equal(sql, expected)

    def test_datediff_minute(self):
        sql = translate(
            "SELECT DATEDIFF(minute,drug_exposure_start_datetime,drug_exposure_end_datetime) FROM drug_exposure;",
            "postgresql",
        )
        expected = (
            "SELECT (EXTRACT(EPOCH FROM (drug_exposure_end_datetime"
            " - drug_exposure_start_datetime)) / 60) FROM drug_exposure;"
        )
        assert_sql_equal(sql, expected)

    def test_datediff_second(self):
        sql = translate(
            "SELECT DATEDIFF(second,drug_exposure_start_datetime,drug_exposure_end_datetime) FROM drug_exposure;",
            "postgresql",
        )
        expected = (
            "SELECT EXTRACT(EPOCH FROM (drug_exposure_end_datetime"
            " - drug_exposure_start_datetime)) FROM drug_exposure;"
        )
        assert_sql_equal(sql, expected)

    def test_with_select(self):
        sql = translate("WITH cte1 AS (SELECT a FROM b) SELECT c FROM cte1;", "postgresql")
        assert_sql_equal(sql, "WITH cte1 AS (SELECT a FROM b) SELECT c FROM cte1;")

    def test_with_select_into(self):
        sql = translate("WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;", "postgresql")
        expected = "CREATE TABLE d \nAS\nWITH cte1 AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1;"
        assert_sql_equal(sql, expected)

    def test_select_into_without_from(self):
        sql = translate("SELECT c INTO d;", "postgresql")
        expected = "CREATE TABLE d AS\nSELECT\nc ;"
        assert_sql_equal(sql, expected)

    def test_with_insert_into_select(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;",
            "postgresql",
        )
        expected = "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;"
        assert_sql_equal(sql, expected)

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NULL\n CREATE TABLE cohort\n(cohort_definition_id INT);",
            "postgresql",
        )
        expected = "CREATE TABLE IF NOT EXISTS cohort\n (cohort_definition_id INT);"
        assert_sql_equal(sql, expected)

    def test_select_random_row(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RAND()) AS rn FROM table) tmp WHERE rn <= 1",
            "postgresql",
        )
        expected = "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn FROM table) tmp WHERE rn <= 1"
        assert_sql_equal(sql, expected)

    def test_hashbytes_md5(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY HASHBYTES('MD5',CAST(person_id AS varchar))) tmp WHERE rn <= 1",
            "postgresql",
        )
        expected = "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY MD5(CAST(person_id AS varchar))) tmp WHERE rn <= 1"
        assert_sql_equal(sql, expected)

    def test_convert_varbinary(self):
        sql = translate(
            "SELECT ROW_NUMBER() OVER CONVERT(VARBINARY, val, 1) rn WHERE rn <= 1",
            "postgresql",
        )
        expected = "SELECT ROW_NUMBER() OVER CAST(CONCAT('x', val) AS BIT(32)) rn WHERE rn <= 1"
        assert_sql_equal(sql, expected)

    def test_top(self):
        sql = translate("SELECT TOP 10 * FROM my_table WHERE a = b;", "postgresql")
        assert_sql_equal(sql, "SELECT * FROM my_table WHERE a = b LIMIT 10;")

    def test_top_subquery(self):
        sql = translate(
            "SELECT name FROM (SELECT TOP 1 name FROM my_table WHERE a = b);",
            "postgresql",
        )
        expected = "SELECT name FROM (SELECT name FROM my_table WHERE a = b LIMIT 1);"
        assert_sql_equal(sql, expected)

    def test_convert_varchar_date(self):
        sql = translate("CONVERT(VARCHAR,start_date,112) FROM table;", "postgresql")
        assert_sql_equal(sql, "TO_CHAR(start_date, 'YYYYMMDD') FROM table;")

    def test_log(self):
        sql = translate("SELECT LOG(number) FROM table", "postgresql")
        assert_sql_equal(sql, "SELECT LN(CAST((number) AS REAL)) FROM table")

    def test_log10(self):
        sql = translate("SELECT LOG10(number) FROM table;", "postgresql")
        assert_sql_equal(sql, "SELECT LOG(10,CAST((number) AS NUMERIC)) FROM table;")

    def test_log_any_base(self):
        sql = translate("SELECT LOG(number, base) FROM table", "postgresql")
        expected = "SELECT LOG(CAST((base) AS NUMERIC),CAST((number) AS NUMERIC)) FROM table"
        assert_sql_equal(sql, expected)

    def test_isnumeric(self):
        sql = translate("SELECT CASE WHEN ISNUMERIC(a) = 1 THEN a ELSE b FROM c;", "postgresql")
        expected = (
            "SELECT CASE WHEN CASE WHEN (CAST(a AS VARCHAR) ~ '^([0-9]+\\.?[0-9]*|\\.[0-9]+)$')"
            " THEN 1 ELSE 0 END = 1 THEN a ELSE b FROM c;"
        )
        assert_sql_equal(sql, expected)

        sql = translate("SELECT a FROM table WHERE ISNUMERIC(a) = 1", "postgresql")
        expected = (
            "SELECT a FROM table WHERE CASE WHEN (CAST(a AS VARCHAR) ~ '^([0-9]+\\.?[0-9]*|\\.[0-9]+)$')"
            " THEN 1 ELSE 0 END = 1"
        )
        assert_sql_equal(sql, expected)

        sql = translate("SELECT a FROM table WHERE ISNUMERIC(a) = 0", "postgresql")
        expected = (
            "SELECT a FROM table WHERE CASE WHEN (CAST(a AS VARCHAR) ~ '^([0-9]+\\.?[0-9]*|\\.[0-9]+)$')"
            " THEN 1 ELSE 0 END = 0"
        )
        assert_sql_equal(sql, expected)

    def test_cte_string_literal_cast(self):
        sql = translate(
            "WITH expression AS(SELECT 'my literal', col1, CAST('other literal' as VARCHAR(MAX)), col2 FROM table WHERE a = b) SELECT * FROM expression ORDER BY 1, 2, 3, 4;",
            "postgresql",
        )
        expected = (
            "WITH expression AS (SELECT CAST('my literal' as TEXT), col1, CAST('other literal' as TEXT),"
            " col2 FROM table WHERE a = b) SELECT * FROM expression ORDER BY 1, 2, 3, 4;"
        )
        assert_sql_equal(sql, expected)

    def test_update_statistics(self):
        sql = translate("UPDATE STATISTICS results_schema.heracles_results;", "postgresql")
        assert_sql_equal(sql, "ANALYZE results_schema.heracles_results;")

    def test_datetime_types(self):
        sql = translate("CREATE TABLE x (a DATETIME2, b DATETIME);", "postgresql")
        assert_sql_equal(sql, "CREATE TABLE x (a TIMESTAMP, b TIMESTAMP);")

    def test_drop_table_if_exists(self):
        sql = translate("DROP TABLE IF EXISTS test;", "postgresql")
        assert_sql_equal(sql, "DROP TABLE IF EXISTS test;")

    def test_comments_in_quotes_1(self):
        sql = (
            "WITH cte_all\nAS (\nSELECT * FROM my_table\n\nUNION ALL\n\n"
            "SELECT '(--12 hours fasting)' AS check_description\n)\n"
            "INSERT INTO cdm.main\nSELECT *\nFROM cte_all;"
        )
        result = translate(sql, "postgresql")
        expected = (
            "WITH cte_all\n AS (SELECT * FROM my_table\nUNION ALL\n"
            "SELECT CAST('(--12 hours fasting)' as TEXT) AS check_description\n)\n"
            "INSERT INTO cdm.main\nSELECT *\nFROM cte_all;"
        )
        assert_sql_equal(result, expected)

    def test_comments_in_quotes_2(self):
        sql = (
            "WITH cte_all\nAS (\nSELECT * FROM my_table\n\nUNION ALL\n\n"
            "SELECT '(/*12 hours fasting)' AS check_description\n)\n"
            "INSERT INTO cdm.main\nSELECT *\nFROM cte_all;"
        )
        result = translate(sql, "postgresql")
        expected = (
            "WITH cte_all\n AS (SELECT * FROM my_table\nUNION ALL\n"
            "SELECT CAST('(/*12 hours fasting)' as TEXT) AS check_description\n)\n"
            "INSERT INTO cdm.main\nSELECT *\nFROM cte_all;"
        )
        assert_sql_equal(result, expected)

    def test_iif(self):
        sql = translate("SELECT IIF(a>b, 1, b) AS max_val FROM table;", "postgresql")
        expected = "SELECT CASE WHEN a>b THEN 1 ELSE b END AS max_val FROM table ;"
        assert_sql_equal(sql, expected)

    def test_alter_table_add_single(self):
        sql = translate("ALTER TABLE my_table ADD a INT;", "postgresql")
        assert_sql_equal(sql, "ALTER TABLE my_table  ADD COLUMN a INT;")

    def test_alter_table_add_multiple(self):
        sql = translate("ALTER TABLE my_table ADD a INT, b INT, c VARCHAR(255);", "postgresql")
        expected = "ALTER TABLE my_table ADD COLUMN a INT, ADD COLUMN b INT, ADD COLUMN c VARCHAR(255);"
        assert_sql_equal(sql, expected)

    def test_alter_table_add_column(self):
        sql = translate("ALTER TABLE my_table ADD COLUMN a INT;", "postgresql")
        assert_sql_equal(sql, "ALTER TABLE my_table ADD COLUMN a INT;")

    def test_alter_table_add_constraint(self):
        sql = translate(
            "ALTER TABLE cdm.MEASUREMENT ADD CONSTRAINT xpk_MEASUREMENT PRIMARY KEY NONCLUSTERED (measurement_id);",
            "postgresql",
        )
        expected = "ALTER TABLE cdm.MEASUREMENT ADD CONSTRAINT xpk_MEASUREMENT PRIMARY KEY (measurement_id);"
        assert_sql_equal(sql, expected)

    def test_alter_table_alter_column(self):
        sql = translate("ALTER TABLE my_table ALTER COLUMN a BIGINT;", "postgresql")
        assert_sql_equal(sql, "ALTER TABLE my_table ALTER COLUMN a TYPE BIGINT;")
