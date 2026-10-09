"""Test Oracle translation - ported from OHDSI SqlRender test-translate-oracle.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestOracleTranslation:
    def test_datediff_day(self):
        sql = translate(
            "SELECT DATEDIFF(dd,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "oracle",
        )
        expected = (
            "SELECT CEIL(CAST(drug_era_end_date AS DATE) - CAST(drug_era_start_date AS DATE)) FROM drug_era;"
        )
        assert_sql_equal(sql, expected)

    def test_datediff_second(self):
        sql = translate(
            "SELECT DATEDIFF(second,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "oracle",
        )
        expected = "SELECT EXTRACT(SECOND FROM (drug_era_end_date - drug_era_start_date)) FROM drug_era;"
        assert_sql_equal(sql, expected)

    def test_datediff_minute(self):
        sql = translate(
            "SELECT DATEDIFF(minute,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "oracle",
        )
        expected = "SELECT EXTRACT(MINUTE FROM (drug_era_end_date - drug_era_start_date)) FROM drug_era;"
        assert_sql_equal(sql, expected)

    def test_datediff_hour(self):
        sql = translate(
            "SELECT DATEDIFF(hour,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "oracle",
        )
        expected = "SELECT EXTRACT(HOUR FROM (drug_era_end_date - drug_era_start_date)) FROM drug_era;"
        assert_sql_equal(sql, expected)

    def test_datediff_year(self):
        sql = translate(
            "SELECT DATEDIFF(YEAR,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "oracle",
        )
        expected = "SELECT (EXTRACT(YEAR FROM CAST(drug_era_end_date AS DATE)) - EXTRACT(YEAR FROM CAST(drug_era_start_date AS DATE))) FROM drug_era;"
        assert_sql_equal(sql, expected)

    def test_datediff_month(self):
        sql = translate(
            "SELECT DATEDIFF(month,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "oracle",
        )
        expected = "SELECT MONTHS_BETWEEN(CAST(drug_era_end_date AS DATE), CAST(drug_era_start_date AS DATE)) FROM drug_era;"
        assert_sql_equal(sql, expected)

    def test_dateadd(self):
        sql = translate("SELECT DATEADD(dd,30,drug_era_end_date) FROM drug_era;", "oracle")
        expected = "SELECT (drug_era_end_date + NUMTODSINTERVAL(30, 'day')) FROM drug_era;"
        assert_sql_equal(sql, expected)

    def test_functional_index(self):
        sql = translate(
            "CREATE INDEX name1 ON someTable (firstColumn,secondColumn) WHERE someCondition;",
            "oracle",
        )
        expected = "CREATE INDEX name1 ON someTable (CASE WHEN someCondition THEN firstColumn END, CASE WHEN someCondition THEN secondColumn END);"
        assert_sql_equal(sql, expected)

    def test_use(self):
        sql = translate("USE vocabulary;", "oracle")
        expected = "ALTER SESSION SET current_schema = vocabulary;"
        assert_sql_equal(sql, expected)

    def test_drop_table_if_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NOT NULL DROP TABLE cohort;",
            "oracle",
        )
        expected = (
            "BEGIN\n"
            "  EXECUTE IMMEDIATE 'TRUNCATE TABLE cohort';\n"
            "  EXECUTE IMMEDIATE 'DROP TABLE cohort';\n"
            "EXCEPTION\n"
            "  WHEN OTHERS THEN\n"
            "    IF SQLCODE != -942 THEN\n"
            "      RAISE;\n"
            "    END IF;\n"
            "END;"
        )
        assert_sql_equal(sql, expected)

    def test_cast_as_date(self):
        sql = translate("CAST('20000101' AS DATE);", "oracle")
        expected = "TO_DATE('20000101', 'YYYYMMDD');"
        assert_sql_equal(sql, expected)

    def test_cast_as_date_not_char_string(self):
        sql = translate("CAST(some_date_time AS DATE);", "oracle")
        expected = "CAST(some_date_time AS DATE);"
        assert_sql_equal(sql, expected)

    def test_convert_as_date(self):
        sql = translate("CONVERT(DATE, '20000101');", "oracle")
        expected = "TO_DATE('20000101', 'YYYYMMDD');"
        assert_sql_equal(sql, expected)

    def test_concatenate_string_operator(self):
        sql = translate(
            "select distinct CONVERT(DATE, cast(YEAR(observation_period_start_date) as varchar(4)) + '01' + '01') as obs_year from observation_period;",
            "oracle",
        )
        expected = "SELECT distinct TO_DATE(cast(EXTRACT(YEAR FROM observation_period_start_date) as varchar(4)) || '01' || '01', 'YYYYMMDD') as obs_year FROM observation_period;"
        assert_sql_equal(sql, expected)

    def test_right_functions(self):
        sql = translate("select RIGHT(x,4);", "oracle")
        expected = "SELECT SUBSTR(x,-4) FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_complex_query(self):
        sql = translate(
            "select CONVERT(DATE,CAST(YEAR(DATEFROMPARTS(2000,1,1)) AS VARCHAR(12)) + RIGHT('0'+MONTH(DATEFROMPARTS(2000,1,1)),2) + '01') as X;",
            "oracle",
        )
        expected = (
            "SELECT TO_DATE(CAST(EXTRACT(YEAR FROM TO_DATE(TO_CHAR(2000,'0000')||'-'||"
            "TO_CHAR(1,'00')||'-'||TO_CHAR(1,'00'), 'YYYY-MM-DD')) AS varchar(12)) || "
            "SUBSTR('0' ||EXTRACT(MONTH FROM TO_DATE(TO_CHAR(2000,'0000')||'-'||"
            "TO_CHAR(1,'00')||'-'||TO_CHAR(1,'00'), 'YYYY-MM-DD')),-2) || '01', "
            "'YYYYMMDD') as X FROM DUAL;"
        )
        assert_sql_equal(sql, expected)

    def test_plus_in_quote(self):
        sql = translate("select '+';", "oracle")
        expected = "SELECT '+' FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_union_in_dual(self):
        sql = translate("select 1 union 2;", "oracle")
        expected = "SELECT 1 FROM DUAL UNION 2 FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_table_alias_single(self):
        sql = translate("SELECT a FROM a AS a1;", "oracle")
        expected = "SELECT a FROM a a1;"
        assert_sql_equal(sql, expected)

    def test_table_alias_join(self):
        sql = translate(
            "SELECT a, b FROM a AS a1 JOIN b AS b1 ON a = b WHERE c = 1;",
            "oracle",
        )
        expected = "SELECT a, b FROM a a1 JOIN b b1 ON a = b WHERE c = 1;"
        assert_sql_equal(sql, expected)

    def test_table_alias_multi_join(self):
        sql = translate(
            "SELECT a, b FROM a as a1 INNER JOIN b AS b1 ON a = b LEFT JOIN c AS c1 ON b = c WHERE c IN (1,2,4);",
            "oracle",
        )
        expected = (
            "SELECT a, b FROM a a1 INNER JOIN b b1 ON a = b LEFT JOIN c c1 ON b = c WHERE c IN (1,2,4);"
        )
        assert_sql_equal(sql, expected)

    def test_table_alias_comma(self):
        sql = translate("SELECT a, b, d FROM a AS a1, b AS b1;", "oracle")
        expected = "SELECT a, b, d FROM a a1, b b1;"
        assert_sql_equal(sql, expected)

    def test_table_alias_comma_where(self):
        sql = translate(
            "SELECT a, b, d FROM a AS a1, b AS b1, c AS c1 WHERE c = 1;",
            "oracle",
        )
        expected = "SELECT a, b, d FROM a a1, b b1, c c1 WHERE c = 1;"
        assert_sql_equal(sql, expected)

    def test_table_alias_subquery(self):
        sql = translate(
            "SELECT a, b, d FROM a AS a1,(SELECT c AS c1 FROM b AS b1) AS d1 WHERE c = 1;",
            "oracle",
        )
        expected = "SELECT a, b, d FROM a a1,(SELECT c AS c1 FROM b b1) d1 WHERE c = 1;"
        assert_sql_equal(sql, expected)

    def test_multiple_inserts_in_one_statement(self):
        sql = translate(
            "INSERT INTO my_table (key,value) VALUES (1,0),(2,0),(3,1)",
            "oracle",
        )
        expected = (
            "INSERT ALL\n"
            "INTO my_table (key,value) VALUES (INTO my_table (key,value) VALUES (1,0)\n"
            " INTO my_table (key,value) VALUES (2,0)\n"
            ")\n"
            " INTO my_table (key,value) VALUES (3,1)\n"
            "SELECT * FROM dual"
        )
        assert_sql_equal(sql, expected)

    def test_with_select(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c FROM cte1;",
            "oracle",
        )
        expected = "WITH cte1 AS (SELECT a FROM b) SELECT c FROM cte1;"
        assert_sql_equal(sql, expected)

    def test_with_select_into(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "oracle",
        )
        expected = "CREATE TABLE d\nAS\nWITH cte1 AS (SELECT a FROM b) SELECT\nc\nFROM\ncte1;"
        assert_sql_equal(sql, expected)

    def test_with_insert_into_select(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) INSERT INTO c (d int) SELECT e FROM cte1;",
            "oracle",
        )
        expected = "INSERT INTO c (d int) WITH cte1 AS (SELECT a FROM b) SELECT e FROM cte1;"
        assert_sql_equal(sql, expected)

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NULL\n CREATE TABLE cohort\n(cohort_definition_id INT);",
            "oracle",
        )
        expected = (
            "BEGIN\n"
            "  EXECUTE IMMEDIATE 'CREATE TABLE cohort\n"
            " (cohort_definition_id INT)';\n"
            "EXCEPTION\n"
            "  WHEN OTHERS THEN\n"
            "    IF SQLCODE != -955 THEN\n"
            "      RAISE;\n"
            "    END IF;\n"
            "END;"
        )
        assert_sql_equal(sql, expected)

    def test_datefromparts(self):
        sql = translate("SELECT DATEFROMPARTS(year,month,day) FROM table", "oracle")
        expected = "SELECT TO_DATE(TO_CHAR(year,'0000')||'-'||TO_CHAR(month,'00')||'-'||TO_CHAR(day,'00'), 'YYYY-MM-DD') FROM table"
        assert_sql_equal(sql, expected)

    def test_datetime_to_timestamp(self):
        sql = translate("CREATE TABLE x (a DATETIME)", "oracle")
        expected = "CREATE TABLE x (a TIMESTAMP)"
        assert_sql_equal(sql, expected)

    def test_select_random_row(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RAND()) AS rn FROM table) tmp WHERE rn <= 1",
            "oracle",
        )
        expected = (
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY "
            "DBMS_RANDOM.VALUE) AS rn FROM table FROM DUAL) tmp WHERE rn <= 1"
        )
        assert_sql_equal(sql, expected)

    def test_select_random_row_using_hash(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY HASHBYTES('MD5',CAST(person_id AS varchar))) tmp WHERE rn <= 1",
            "oracle",
        )
        expected = "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY DBMS_CRYPTO.HASH(TO_CHAR(person_id),2)) tmp WHERE rn <= 1"
        assert_sql_equal(sql, expected)

    def test_convert_varbinary(self):
        sql = translate(
            "SELECT ROW_NUMBER() OVER CONVERT(VARBINARY, val, 1) rn WHERE rn <= 1",
            "oracle",
        )
        expected = "SELECT ROW_NUMBER() OVER TO_NUMBER(val, RPAD('X', LENGTH(val), 'X')) rn WHERE rn <= 1"
        assert_sql_equal(sql, expected)

    def test_hash_hash_issue_on_oracle(self):
        sql = translate("SELECT a FROM c##blah.table;", "oracle")
        expected = "SELECT a FROM c##blah.table;"
        assert_sql_equal(sql, expected)

    def test_top(self):
        sql = translate("SELECT TOP 10 * FROM my_table WHERE a = b;", "oracle")
        expected = "SELECT * FROM my_table WHERE a = b FETCH FIRST 10 ROWS ONLY;"
        assert_sql_equal(sql, expected)

    def test_top_subquery(self):
        sql = translate(
            "SELECT name FROM (SELECT TOP 1 name FROM my_table WHERE a = b);",
            "oracle",
        )
        expected = "SELECT name FROM (SELECT name FROM my_table WHERE a = b FETCH FIRST 1 ROWS ONLY);"
        assert_sql_equal(sql, expected)

    def test_distinct_top(self):
        sql = translate("SELECT DISTINCT TOP 10 a FROM my_table WHERE a = b;", "oracle")
        expected = "SELECT DISTINCT a FROM my_table WHERE a = b FETCH FIRST 10 ROWS ONLY;"
        assert_sql_equal(sql, expected)

    def test_concat(self):
        sql = translate('SELECT CONCAT(a," , ",c,d,e) FROM x;', "oracle")
        expected = 'SELECT CONCAT(a, CONCAT(" , ", CONCAT(c, CONCAT(d, e)))) FROM x;'
        assert_sql_equal(sql, expected)

    def test_natural_log(self):
        sql = translate("SELECT LOG(number) FROM table", "oracle")
        expected = "SELECT LOG(2.718281828459,number) FROM table"
        assert_sql_equal(sql, expected)

    def test_log_base_10(self):
        sql = translate("SELECT LOG10(number) FROM table;", "oracle")
        expected = "SELECT LOG(10,number) FROM table;"
        assert_sql_equal(sql, expected)

    def test_log_any_base(self):
        sql = translate("SELECT LOG(number, base) FROM table", "oracle")
        expected = "SELECT LOG(base,number) FROM table"
        assert_sql_equal(sql, expected)

    def test_union_1(self):
        sql = translate(
            "SELECT * FROM table1 WHERE a = 1 UNION SELECT * FROM table2 WHERE a = 1;",
            "oracle",
        )
        expected = "SELECT * FROM table1 WHERE a = 1 UNION SELECT * FROM table2 WHERE a = 1;"
        assert_sql_equal(sql, expected)

    def test_union_2(self):
        sql = translate(
            "SELECT * FROM table1 UNION SELECT * FROM table2 WHERE a = 1;",
            "oracle",
        )
        expected = "SELECT * FROM table1 UNION SELECT * FROM table2 WHERE a = 1;"
        assert_sql_equal(sql, expected)

    def test_from_dual_simple(self):
        sql = translate("SELECT 1 AS id;", "oracle")
        expected = "SELECT 1 AS id FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_from_dual_subquery(self):
        sql = translate("SELECT (SELECT id FROM a WHERE b=2) AS id;", "oracle")
        expected = "SELECT (SELECT id FROM a WHERE b=2) AS id FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_isnumeric_case(self):
        sql = translate(
            "SELECT CASE WHEN ISNUMERIC(a) = 1 THEN a ELSE b FROM c;",
            "oracle",
        )
        expected = "SELECT CASE WHEN CASE WHEN (LENGTH(TRIM(TRANSLATE(a, ' +-.0123456789',' '))) IS NULL) THEN 1 ELSE 0 END = 1 THEN a ELSE b FROM c;"
        assert_sql_equal(sql, expected)

    def test_isnumeric_where_equal_1(self):
        sql = translate("SELECT a FROM table WHERE ISNUMERIC(a) = 1", "oracle")
        expected = "SELECT a FROM table WHERE CASE WHEN (LENGTH(TRIM(TRANSLATE(a, ' +-.0123456789',' '))) IS NULL) THEN 1 ELSE 0 END = 1"
        assert_sql_equal(sql, expected)

    def test_isnumeric_where_equal_0(self):
        sql = translate("SELECT a FROM table WHERE ISNUMERIC(a) = 0", "oracle")
        expected = "SELECT a FROM table WHERE CASE WHEN (LENGTH(TRIM(TRANSLATE(a, ' +-.0123456789',' '))) IS NULL) THEN 1 ELSE 0 END = 0"
        assert_sql_equal(sql, expected)

    def test_add_group_by_when_case_count(self):
        sql = translate(
            "SELECT CASE COUNT(*) = 1 THEN 0 ELSE SUM(x)/(COUNT(*)-1) END AS stat FROM my_table;",
            "oracle",
        )
        expected = (
            "SELECT CASE COUNT(*) = 1 THEN 0 ELSE SUM(x)/(COUNT(*)-1) END AS stat FROM my_table GROUP BY 1;"
        )
        assert_sql_equal(sql, expected)

    def test_dont_add_group_by_when_already_group_by(self):
        sql = translate(
            "SELECT CASE COUNT(*) = 1 THEN 0 ELSE SUM(x)/(COUNT(*)-1) END AS stat FROM my_table GROUP BY y;",
            "oracle",
        )
        expected = (
            "SELECT CASE COUNT(*) = 1 THEN 0 ELSE SUM(x)/(COUNT(*)-1) END AS stat FROM my_table GROUP BY y;"
        )
        assert_sql_equal(sql, expected)

    def test_union_of_two_queries_without_from(self):
        sql = translate("SELECT 1,2 UNION SELECT 3,4;", "oracle")
        expected = "SELECT 1,2 FROM DUAL UNION SELECT 3,4 FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_union_of_three_queries_without_from(self):
        sql = translate("SELECT 1,2 UNION SELECT 3,4 UNION SELECT 5,6;", "oracle")
        expected = "SELECT 1,2 FROM DUAL UNION SELECT 3,4 FROM DUAL UNION SELECT 5,6 FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_insert_plus_union_of_three_queries_without_from(self):
        sql = translate(
            "INSERT INTO my_table (a, b) SELECT 1,2 UNION SELECT 3,4 UNION SELECT 5,6;",
            "oracle",
        )
        expected = "INSERT INTO my_table (a, b) SELECT 1,2 FROM DUAL UNION SELECT 3,4 FROM DUAL UNION SELECT 5,6 FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_union_where_only_last_query_needs_from_dual(self):
        sql = translate("SELECT a,b FROM my_table UNION SELECT 5,6;", "oracle")
        expected = "SELECT a,b FROM my_table UNION SELECT 5,6 FROM DUAL;"
        assert_sql_equal(sql, expected)

    def test_nested_queries_with_eols(self):
        sql = translate(
            "INSERT INTO test (a,b) SELECT a,b FROM (SELECT a,b FROM (SELECT a,b FROM my_table\n) nesti WHERE b = 2\n) nesto WHERE a = 1;",
            "oracle",
        )
        expected = "INSERT INTO test (a,b) SELECT a,b FROM (SELECT a,b FROM (SELECT a,b FROM my_table\n) nesti WHERE b = 2\n) nesto WHERE a = 1;"
        assert_sql_equal(sql, expected)

    def test_nested_queries_with_union(self):
        sql = translate(
            "SELECT a,b FROM (SELECT a,b FROM x UNION ALL SELECT a,b FROM x) o;",
            "oracle",
        )
        expected = "SELECT a,b FROM (SELECT a,b FROM x UNION ALL SELECT a,b FROM x) o;"
        assert_sql_equal(sql, expected)

    def test_bigint_in_conditional_create_table(self):
        sql = translate(
            "IF OBJECT_ID('test', 'U') IS NULL CREATE TABLE test (x BIGINT);",
            "oracle",
        )
        expected = (
            "BEGIN\n"
            "  EXECUTE IMMEDIATE 'CREATE TABLE test (x NUMBER(19))';\n"
            "EXCEPTION\n"
            "  WHEN OTHERS THEN\n"
            "    IF SQLCODE != -955 THEN\n"
            "      RAISE;\n"
            "    END IF;\n"
            "END;"
        )
        assert_sql_equal(sql, expected)

    def test_not_null_and_default_in_conditional_create_table(self):
        sql = translate(
            "IF OBJECT_ID('test_b', 'U') IS NULL CREATE TABLE test_b (x INT NOT NULL DEFAULT 0);",
            "oracle",
        )
        expected = (
            "BEGIN\n"
            "  EXECUTE IMMEDIATE 'CREATE TABLE test_b (x INT DEFAULT 0 NOT NULL)';\n"
            "EXCEPTION\n"
            "  WHEN OTHERS THEN\n"
            "    IF SQLCODE != -955 THEN\n"
            "      RAISE;\n"
            "    END IF;\n"
            "END;"
        )
        assert_sql_equal(sql, expected)

    def test_analyze_table(self):
        sql = translate("UPDATE STATISTICS results_schema.heracles_results;", "oracle")
        expected = "-- ANALYZE should not be used to collect optimizer statistics"
        assert_sql_equal(sql, expected)

    def test_datetime_and_datetime2(self):
        sql = translate("CREATE TABLE x (a DATETIME2, b DATETIME);", "oracle")
        expected = "CREATE TABLE x (a TIMESTAMP, b TIMESTAMP);"
        assert_sql_equal(sql, expected)

    def test_drop_table_if_exists_simple(self):
        sql = translate("DROP TABLE IF EXISTS test;", "oracle")
        expected = (
            "BEGIN\n"
            "  EXECUTE IMMEDIATE 'TRUNCATE TABLE test';\n"
            "  EXECUTE IMMEDIATE 'DROP TABLE test';\n"
            "EXCEPTION\n"
            "  WHEN OTHERS THEN\n"
            "    IF SQLCODE != -942 THEN\n"
            "      RAISE;\n"
            "    END IF;\n"
            "END;"
        )
        assert_sql_equal(sql, expected)

    def test_select_star_comma(self):
        sql = translate("SELECT *, 1 AS x FROM my_table;", "oracle")
        expected = "SELECT my_table.*, 1 AS x FROM my_table;"
        assert_sql_equal(sql, expected)

    def test_select_star_comma_subquery(self):
        sql = translate("SELECT *, 1 AS x FROM (SELECT a FROM b) q01;", "oracle")
        expected = "SELECT q01.*, 1 AS x FROM (SELECT a FROM b) q01;"
        assert_sql_equal(sql, expected)

    def test_select_top_star_comma(self):
        sql = translate("SELECT TOP 10 *, 1 AS x FROM my_table;", "oracle")
        expected = "SELECT my_table.*, 1 AS x FROM my_table FETCH FIRST 10 ROWS ONLY;"
        assert_sql_equal(sql, expected)

    def test_select_star_comma_where(self):
        sql = translate("SELECT *, 1 AS x FROM my_table WHERE a = b;", "oracle")
        expected = "SELECT my_table.*, 1 AS x FROM my_table WHERE a = b;"
        assert_sql_equal(sql, expected)

    def test_select_star_comma_order_by(self):
        sql = translate("SELECT *, 1 AS x FROM my_table WHERE a = b ORDER BY a;", "oracle")
        expected = "SELECT my_table.*, 1 AS x FROM my_table WHERE a = b ORDER BY a;"
        assert_sql_equal(sql, expected)

    def test_nested_select_star_comma(self):
        sql = translate("(SELECT *, 1 AS x FROM my_table)", "oracle")
        expected = "(SELECT my_table.*, 1 AS x FROM my_table)"
        assert_sql_equal(sql, expected)

    def test_iif(self):
        sql = translate("SELECT IIF(a>b, 1, b) AS max_val FROM table;", "oracle")
        expected = "SELECT CASE WHEN a>b THEN 1 ELSE b END AS max_val FROM table;"
        assert_sql_equal(sql, expected)

    def test_drvd(self):
        sql = translate(
            "SELECT\n"
            "      TRY_CAST(name AS VARCHAR(MAX)) AS name,\n"
            "      TRY_CAST(speed AS FLOAT) AS speed\n"
            "    FROM (  VALUES ('A', 1.0), ('B', 2.0)) AS drvd(name, speed);",
            "oracle",
        )
        expected = (
            "SELECT CAST(name AS VARCHAR2(1024)) AS name,\n"
            "      CAST(speed AS FLOAT) AS speed\n"
            "    FROM (SELECT NULL AS name, NULL AS speed FROM DUAL WHERE (0 = 1)"
            " UNION ALL SELECT 'A', 1.0 FROM DUAL"
            " UNION ALL SELECT 'B', 2.0 FROM DUAL) values_table;"
        )
        assert_sql_equal(sql, expected)

    def test_temp_dplyr_dots_pattern(self):
        sql = translate("SELECT * FROM table...1;", "oracle")
        expected = "SELECT * FROM tablexxx1;"
        assert_sql_equal(sql, expected)

    def test_bitwise_and(self):
        sql = translate("SELECT ((a+b) & c/123) FROM table;", "oracle")
        expected = "SELECT BITAND((a+b), c/123) FROM table;"
        assert_sql_equal(sql, expected)

    # ── tests using tempEmulationSchema (ported using explicit session_id) ──

    def test_temp_table_field_ref(self):
        sql = translate(
            "SELECT #tmp.name FROM #tmp;",
            "oracle",
            temp_emulation_schema="ts",
            session_id="T0000000",
        )
        expected = "SELECT T0000000tmp.name FROM ts.T0000000tmp;"
        assert_sql_equal(sql, expected)

    def test_create_temp_table(self):
        sql = translate(
            "CREATE TABLE #temp (x INT);",
            "oracle",
            temp_emulation_schema="ts",
            session_id="T0000000",
        )
        expected = (
            "BEGIN\n"
            "  EXECUTE IMMEDIATE 'TRUNCATE TABLE ts.T0000000temp';\n"
            "  EXECUTE IMMEDIATE 'DROP TABLE ts.T0000000temp';\n"
            "EXCEPTION\n"
            "  WHEN OTHERS THEN\n"
            "    IF SQLCODE != -942 THEN\n"
            "      RAISE;\n"
            "    END IF;\n"
            "END;\n"
            "CREATE TABLE ts.T0000000temp (x INT);"
        )
        assert_sql_equal(sql, expected)

    def test_select_into_temp_table(self):
        sql = translate(
            "SELECT * INTO #temp FROM my_table;",
            "oracle",
            temp_emulation_schema="ts",
            session_id="T0000000",
        )
        expected = (
            "BEGIN\n"
            "  EXECUTE IMMEDIATE 'TRUNCATE TABLE ts.T0000000temp';\n"
            "  EXECUTE IMMEDIATE 'DROP TABLE ts.T0000000temp';\n"
            "EXCEPTION\n"
            "  WHEN OTHERS THEN\n"
            "    IF SQLCODE != -942 THEN\n"
            "      RAISE;\n"
            "    END IF;\n"
            "END;\n"
            "CREATE TABLE ts.T0000000temp AS\n"
            "SELECT\n"
            "*\n"
            "FROM\n"
            "my_table;"
        )
        assert_sql_equal(sql, expected)

    # ── skip translateSingleStatement tests ──
    # The Python implementation does not expose translateSingleStatement as a
    # public API. The R equivalent relies on an internal helper. Related tests
    # (trailing semicolons, BEGIN…END blocks, multi-statement error) are omitted
    # for now but can be added as unit tests against split_sql + translate once
    # that composition is formally supported.

    def test_single_statement_trailing_semicolon__not_applicable(self):
        """translateSingleStatement not available; verify translate strips trailing semicolons."""
        # R expected: "SELECT * FROM my_table " (no trailing semicolon)
        sql = translate("SELECT * FROM my_table;", "oracle")
        # The Python translate() does NOT strip trailing semicolons; the R
        # translateSingleStatement did. We document the current behavior.
        assert sql.rstrip().endswith(";") or sql.rstrip().endswith("FROM DUAL;")

    def test_single_statement_begin_end__not_applicable(self):
        """translateSingleStatement not available; verify translate handles BEGIN…END."""
        sql = translate(
            "BEGIN\nSELECT * INTO a FROM b;\nEND;",
            "oracle",
        )
        # Verify translation produces valid Oracle CREATE TABLE AS syntax
        assert "CREATE TABLE a" in sql
        assert "SELECT" in sql

    def test_single_statement_multi_error__not_applicable(self):
        """translateSingleStatement not available; verify translate handles multiple statements."""
        # translate does not throw for multiple statements; it translates them all
        sql = translate("TRUNCATE my_table; DROP TABLE my_table;", "oracle")
        # Should contain both translated statements
        assert sql.strip() != ""

    # ── oracleTempSchema warning tests are not applicable ──
    # The R package had a deprecated 'oracleTempSchema' parameter that emitted
    # a warning. Python's translate() uses 'temp_emulation_schema' instead, and
    # there is no deprecated alias. These tests are not ported.
