"""Test InterSystems IRIS translation - ported from OHDSI SqlRender test-translate-iris.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal

SESSION_ID = "S0000000"


class TestIrisTranslation:
    def test_string_concatenation_concat_three(self):
        sql = translate("SELECT CONCAT(a, 'b', c)", "iris")
        assert_sql_equal(sql, "SELECT a || 'b' || c")

    def test_string_concatenation_concat_many(self):
        sql = translate("SELECT CONCAT(a, 'b', c, d, e, e, f)", "iris")
        assert_sql_equal(sql, "SELECT a || 'b' || c || d || e || e || f")

    def test_string_concatenation_plus(self):
        sql = translate(
            "SELECT CAST(a AS VARCHAR) + CAST(b AS VARCHAR(10)) + CAST(c AS VARCHAR) + 'd'",
            "iris",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(a AS VARCHAR) || CAST(b AS varchar(10)) || CAST(c AS VARCHAR) || 'd'",
        )

    def test_string_concatenation_dob(self):
        sql = translate("SELECT CONCAT(p.year_of_birth, 11, 11)", "iris")
        assert_sql_equal(sql, "SELECT p.year_of_birth||'-'||11||'-'||11")

    def test_datefromparts(self):
        sql = translate("SELECT DATEFROMPARTS(yyyy, mm, dd)", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(TO_CHAR(yyyy,'FM0000')||'-'||TO_CHAR(mm,'FM00')||'-'||TO_CHAR(dd,'FM00'), 'YYYY-MM-DD')",
        )

    def test_datetimefromparts(self):
        sql = translate("SELECT DATETIMEFROMPARTS(yyyy, mm, dd, hh, mi, ss, ms)", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_TIMESTAMP(TO_CHAR(yyyy,'FM0000')||'-'||TO_CHAR(mm,'FM00')||'-'||TO_CHAR(dd,'FM00')||' '||TO_CHAR(hh,'FM00')||':'||TO_CHAR(mi,'FM00')||':'||TO_CHAR(ss,'FM00')||'.'||TO_CHAR(ms,'FM000'), 'YYYY-MM-DD HH24:MI:SS.FF')",
        )

    def test_implicit_ctas(self):
        sql = translate("SELECT a, b INTO t_new FROM t;", "iris")
        assert_sql_equal(sql, "CREATE TABLE t_new AS SELECT a, b FROM t;")

    def test_implicit_cttas(self):
        sql = translate(
            "SELECT a, b INTO #t_new FROM t;",
            "iris",
            session_id=SESSION_ID,
        )
        assert_sql_equal(
            sql,
            f"CREATE GLOBAL TEMPORARY TABLE {SESSION_ID}t_new AS SELECT a, b FROM t;",
        )

    def test_dateadd_d(self):
        sql = translate("SELECT DATEADD(d, 1, '2007-07-28') AS dt", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(DATEADD(d,1,'2007-07-28'),'YYYY-MM-DD HH:MI:SS') AS dt",
        )

    def test_dateadd_dd(self):
        sql = translate("SELECT DATEADD(dd, 1, '2007-07-28') AS dt", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(DATEADD(dd,1,'2007-07-28'),'YYYY-MM-DD HH:MI:SS') AS dt",
        )

    def test_dateadd_day(self):
        sql = translate("SELECT DATEADD(day, 1, '2007-07-28') AS dt", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(DATEADD(day,1,'2007-07-28'),'YYYY-MM-DD HH:MI:SS') AS dt",
        )

    def test_dateadd_m(self):
        sql = translate("SELECT DATEADD(m, 1, '2007-07-28') AS dt", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(DATEADD(m,1,'2007-07-28'),'YYYY-MM-DD HH:MI:SS') AS dt",
        )

    def test_dateadd_mm(self):
        sql = translate("SELECT DATEADD(mm, 1, '2007-07-28') AS dt", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(DATEADD(mm,1,'2007-07-28'),'YYYY-MM-DD HH:MI:SS') AS dt",
        )

    def test_dateadd_yy(self):
        sql = translate("SELECT DATEADD(yy, 1, '2007-07-28') AS dt", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(DATEADD(yy,1,'2007-07-28'),'YYYY-MM-DD HH:MI:SS') AS dt",
        )

    def test_dateadd_yyyy(self):
        sql = translate("SELECT DATEADD(yyyy, 1, '2007-07-28') AS dt", "iris")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(DATEADD(yyyy,1,'2007-07-28'),'YYYY-MM-DD HH:MI:SS') AS dt",
        )

    def test_reserved_word_domain(self):
        sql = translate("SELECT t.domain, 'domain' FROM omopcdm.domain AS t", "iris")
        assert_sql_equal(sql, 'SELECT t."DOMAIN", \'domain\' FROM omopcdm."DOMAIN" AS t')

    def test_reserved_words_aggregates(self):
        sql = translate(
            "SELECT MIN(x) AS min, MAX(x) AS max, COUNT(x) as COUNT FROM t",
            "iris",
        )
        assert_sql_equal(
            sql,
            'SELECT MIN(x) AS "MIN", MAX(x) AS "MAX", COUNT(x) AS "COUNT" FROM t',
        )

    def test_function_names(self):
        sql = translate(
            "SELECT STDEV(x), STDEV_POP(x), STDEV_SAMP(x), EOMONTH(dt) FROM t",
            "iris",
        )
        assert_sql_equal(
            sql,
            "SELECT STDDEV(x), STDDEV_POP(x), STDDEV_SAMP(x), LAST_DAY(dt) FROM t",
        )

    def test_from_values_clause(self):
        sql = translate(
            "SELECT * FROM (SELECT TRY_CAST(a AS INT) AS a, TRY_CAST(b AS DOUBLE) AS b FROM (VALUES (1, 2), (2, 3)) AS drvd(a, b);",
            "iris",
        )
        assert_sql_equal(
            sql,
            "SELECT * FROM (SELECT CAST(a AS INT) AS a, CAST(b AS DOUBLE) AS b FROM ((SELECT NULL AS a, NULL AS b WHERE (0 = 1)) UNION ALL (SELECT 1, 2) UNION ALL (SELECT 2, 3)) AS values_table;",
        )

    def test_ddl_with_cte_permanent(self):
        sql = translate(
            "WITH a AS (SELECT 123 as test), b AS (SELECT test FROM t_test) CREATE TABLE t AS SELECT * FROM a UNION b;",
            "iris",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE t AS WITH a AS (SELECT 123 as test), b AS (SELECT test FROM t_test) SELECT * FROM a UNION b;",
        )

    def test_ddl_with_cte_temp(self):
        sql = translate(
            "WITH a AS (SELECT 123 as test), b AS (SELECT test FROM t_test) CREATE TABLE #t AS SELECT * FROM a UNION b;",
            "iris",
            session_id=SESSION_ID,
        )
        assert_sql_equal(
            sql,
            f"CREATE GLOBAL TEMPORARY TABLE {SESSION_ID}t AS WITH a AS (SELECT 123 as test), b AS (SELECT test FROM t_test) SELECT * FROM a UNION b;",
        )

    def test_ddl_with_cte_select_into_temp(self):
        sql = translate(
            "WITH a AS (SELECT 123 as test) SELECT * INTO #t FROM a;",
            "iris",
            session_id=SESSION_ID,
        )
        assert_sql_equal(
            sql,
            f"CREATE GLOBAL TEMPORARY TABLE {SESSION_ID}t AS WITH a AS (SELECT 123 as test) SELECT * FROM a;",
        )

    def test_ctas_with_order_by(self):
        sql = translate("CREATE TABLE t AS (SELECT x FROM tt) ORDER BY x;", "iris")
        assert_sql_equal(sql, "CREATE TABLE t AS SELECT x FROM tt ORDER BY x;")

    def test_ctas_with_order_by_desc(self):
        sql = translate("CREATE TABLE t AS (SELECT x FROM tt) ORDER BY x DESC;", "iris")
        assert_sql_equal(sql, "CREATE TABLE t AS SELECT x FROM tt ORDER BY x DESC;")

    def test_ctas_with_order_by_inner(self):
        sql = translate("CREATE TABLE t AS (SELECT x FROM tt ORDER BY x);", "iris")
        assert_sql_equal(sql, "CREATE TABLE t AS SELECT x FROM tt ORDER BY x;")
