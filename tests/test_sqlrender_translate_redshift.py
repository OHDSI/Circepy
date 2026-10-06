"""Test Redshift translation - ported from OHDSI SqlRender test-translate-redshift.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestRedshiftTranslation:
    def test_varchar_max(self):
        sql = translate("VARCHAR(MAX)", "redshift")
        assert_sql_equal(sql, "VARCHAR(MAX)")

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('cohort', 'U') IS NULL\n CREATE TABLE cohort\n(cohort_definition_id INT);",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  IF NOT EXISTS  cohort\n  (cohort_definition_id INT)\nDISTSTYLE ALL;",
        )

    def test_datefromparts(self):
        sql = translate("SELECT DATEFROMPARTS(year,month,day) FROM table", "redshift")
        assert_sql_equal(
            sql,
            "SELECT TO_DATE(TO_CHAR(year,'0000FM')||'-'||TO_CHAR(month,'00FM')||'-'||TO_CHAR(day,'00FM'), 'YYYY-MM-DD') FROM table",
        )

    def test_select_random_row(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RAND()) AS rn FROM table) tmp WHERE rn <= 1",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY RANDOM()) AS rn FROM table) tmp WHERE rn <= 1",
        )

    def test_select_random_row_using_hash(self):
        sql = translate(
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY HASHBYTES('MD5',CAST(person_id AS varchar))) tmp WHERE rn <= 1",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT column FROM (SELECT column, ROW_NUMBER() OVER (ORDER BY MD5(CAST(person_id AS varchar))) tmp WHERE rn <= 1",
        )

    def test_convert_varbinary(self):
        sql = translate(
            "SELECT ROW_NUMBER() OVER CONVERT(VARBINARY, val, 1) rn WHERE rn <= 1",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT ROW_NUMBER() OVER STRTOL(LEFT(val, 15), 16) rn WHERE rn <= 1",
        )

    def test_hint_distribute_on_key_select_into(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id)\nSELECT * INTO #my_table FROM other_table;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id)\nCREATE TABLE  #my_table\nDISTKEY(row_id)\nAS\nSELECT\n * \nFROM\n other_table;",
        )

    def test_hint_distribute_on_key_create_table(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id)\nCREATE TABLE my_table (row_id INT);",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id)\nCREATE TABLE my_table (row_id INT)\nDISTKEY(row_id);",
        )

    def test_hint_distribute_on_random_select_into(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_RANDOM\nSELECT * INTO #my_table FROM other_table;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_RANDOM\nCREATE TABLE  #my_table\nDISTSTYLE EVEN\nAS\nSELECT\n * \nFROM\n other_table;",
        )

    def test_hint_distribute_on_random_create_table(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_RANDOM\nCREATE TABLE my_table (row_id INT);",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_RANDOM\nCREATE TABLE my_table (row_id INT)\nDISTSTYLE EVEN;",
        )

    def test_natural_log(self):
        sql = translate("SELECT LOG(number) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT LN(CAST((number) AS REAL)) FROM table")

    def test_log_base_10(self):
        sql = translate("SELECT LOG10(number) FROM table;", "redshift")
        assert_sql_equal(sql, "SELECT LOG(CAST((number) AS REAL)) FROM table;")

    def test_log_any_base(self):
        sql = translate("SELECT LOG(number, base) FROM table", "redshift")
        assert_sql_equal(
            sql,
            "SELECT (LN(CAST((number) AS REAL))/LN(CAST(( base) AS REAL))) FROM table",
        )

    def test_dateadd_dd(self):
        sql = translate(
            "SELECT DATEADD(dd, 30, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(day, CAST(30 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_mm(self):
        sql = translate(
            "SELECT DATEADD(mm, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(month, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_m(self):
        sql = translate(
            "SELECT DATEADD(m, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(month, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_yyyy(self):
        sql = translate(
            "SELECT DATEADD(yyyy, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(year, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_yy(self):
        sql = translate(
            "SELECT DATEADD(yy, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(year, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_qq(self):
        sql = translate(
            "SELECT DATEADD(qq, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(quarter, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_q(self):
        sql = translate(
            "SELECT DATEADD(q, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(quarter, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_wk(self):
        sql = translate(
            "SELECT DATEADD(wk, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(week, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_ww(self):
        sql = translate(
            "SELECT DATEADD(ww, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(week, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_hh(self):
        sql = translate(
            "SELECT DATEADD(hh, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(hour, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

        sql = translate(
            "SELECT DATEADD(hour, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(hour, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_mi(self):
        sql = translate(
            "SELECT DATEADD(mi, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(minute, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

        sql = translate(
            "SELECT DATEADD(minute, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(minute, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_ss(self):
        sql = translate(
            "SELECT DATEADD(ss, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(second, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

        sql = translate(
            "SELECT DATEADD(second, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(second, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_dateadd_mcs(self):
        sql = translate(
            "SELECT DATEADD(mcs, 3, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEADD(microsecond, CAST(3 as int), drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_dd(self):
        sql = translate(
            "SELECT DATEDIFF(dd, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(day, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_year(self):
        sql = translate(
            "SELECT DATEDIFF(YEAR,drug_era_start_date,drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(YEAR,drug_era_start_date,drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_m(self):
        sql = translate(
            "SELECT DATEDIFF(m, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(month, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_mm(self):
        sql = translate(
            "SELECT DATEDIFF(mm, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(month, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_yyyy(self):
        sql = translate(
            "SELECT DATEDIFF(yyyy, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(year, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_yy(self):
        sql = translate(
            "SELECT DATEDIFF(yy, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(year, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_qq(self):
        sql = translate(
            "SELECT DATEDIFF(qq, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(quarter, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_q(self):
        sql = translate(
            "SELECT DATEDIFF(q, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(quarter, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_wk(self):
        sql = translate(
            "SELECT DATEDIFF(wk, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(week, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_ww(self):
        sql = translate(
            "SELECT DATEDIFF(ww, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(week, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_hh(self):
        sql = translate(
            "SELECT DATEDIFF(hh, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(hour, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

        sql = translate(
            "SELECT DATEDIFF(hour, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(hour, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_mi(self):
        sql = translate(
            "SELECT DATEDIFF(mi, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(minute, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

        sql = translate(
            "SELECT DATEDIFF(minute, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(minute, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_n(self):
        sql = translate(
            "SELECT DATEDIFF(n, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(minute, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_ss(self):
        sql = translate(
            "SELECT DATEDIFF(ss, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(second, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

        sql = translate(
            "SELECT DATEDIFF(second, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(second, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_mcs(self):
        sql = translate(
            "SELECT DATEDIFF(mcs, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(microsecond, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_dd(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(dd, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(day, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_m(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(m, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(month, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_mm(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(mm, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(month, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_yyyy(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(yyyy, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(year, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_yy(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(yy, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(year, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_qq(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(qq, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(quarter, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_q(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(q, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(quarter, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_wk(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(wk, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(week, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_ww(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(ww, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(week, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_hh(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(hh, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(hour, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_mi(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(mi, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(minute, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_n(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(n, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(minute, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_ss(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(ss, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(second, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datediff_big_mcs(self):
        sql = translate(
            "SELECT DATEDIFF_BIG(mcs, drug_era_start_date, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT DATEDIFF(microsecond, drug_era_start_date, drug_era_end_date) FROM drug_era;",
        )

    def test_datepart_dd(self):
        sql = translate(
            "SELECT DATEPART(dd, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(day, drug_era_end_date) FROM drug_era;")

        sql = translate(
            "SELECT DATEPART(day, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(day, drug_era_end_date) FROM drug_era;")

    def test_datepart_m(self):
        sql = translate(
            "SELECT DATEPART(m, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(month, drug_era_end_date) FROM drug_era;")

    def test_datepart_mm(self):
        sql = translate(
            "SELECT DATEPART(mm, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(month, drug_era_end_date) FROM drug_era;")

    def test_datepart_yyyy(self):
        sql = translate(
            "SELECT DATEPART(yyyy, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(year, drug_era_end_date) FROM drug_era;")

    def test_datepart_yy(self):
        sql = translate(
            "SELECT DATEPART(yy, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(year, drug_era_end_date) FROM drug_era;")

    def test_datepart_qq(self):
        sql = translate(
            "SELECT DATEPART(qq, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(quarter, drug_era_end_date) FROM drug_era;")

    def test_datepart_q(self):
        sql = translate(
            "SELECT DATEPART(q, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(quarter, drug_era_end_date) FROM drug_era;")

    def test_datepart_wk(self):
        sql = translate(
            "SELECT DATEPART(wk, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(week, drug_era_end_date) FROM drug_era;")

    def test_datepart_ww(self):
        sql = translate(
            "SELECT DATEPART(ww, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(week, drug_era_end_date) FROM drug_era;")

    def test_datepart_hh(self):
        sql = translate(
            "SELECT DATEPART(hh, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(hour, drug_era_end_date) FROM drug_era;")

        sql = translate(
            "SELECT DATEPART(hour, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(hour, drug_era_end_date) FROM drug_era;")

    def test_datepart_mi(self):
        sql = translate(
            "SELECT DATEPART(mi, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(minute, drug_era_end_date) FROM drug_era;")

        sql = translate(
            "SELECT DATEPART(minute, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(minute, drug_era_end_date) FROM drug_era;")

    def test_datepart_n(self):
        sql = translate(
            "SELECT DATEPART(n, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(minute, drug_era_end_date) FROM drug_era;")

    def test_datepart_ss(self):
        sql = translate(
            "SELECT DATEPART(ss, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(second, drug_era_end_date) FROM drug_era;")

        sql = translate(
            "SELECT DATEPART(second, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(second, drug_era_end_date) FROM drug_era;")

    def test_datepart_mcs(self):
        sql = translate(
            "SELECT DATEPART(mcs, drug_era_end_date) FROM drug_era;",
            "redshift",
        )
        assert_sql_equal(sql, "SELECT DATEPART(microsecond, drug_era_end_date) FROM drug_era;")

    def test_datetimefromparts(self):
        sql = translate(
            "SELECT DATETIMEFROMPARTS(year,month,day,hour,minute,second,millisecond) FROM table",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(TO_CHAR(year,'0000FM')||'-'||TO_CHAR(month,'00FM')||'-'||TO_CHAR(day,'00FM')||' '||TO_CHAR(hour,'00FM')||':'||TO_CHAR(minute,'00FM')||':'||TO_CHAR(second,'00FM')||'.'||TO_CHAR(millisecond,'000FM') as TIMESTAMP) FROM table",
        )

    def test_eomonth(self):
        sql = translate("SELECT EOMONTH(date) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT LAST_DAY(date) FROM table")

    def test_variance(self):
        sql = translate("SELECT VAR(a) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT VARIANCE(a) FROM table")

    def test_square(self):
        sql = translate("SELECT SQUARE(a + b) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT ((a + b) * (a + b)) FROM table")

    def test_newid(self):
        sql = translate("SELECT NEWID()", "redshift")
        assert_sql_equal(sql, "SELECT MD5(RANDOM()::TEXT || GETDATE()::TEXT)")

    def test_bool_type(self):
        sql = translate("CREATE TABLE table ( col BIT not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col BOOLEAN not null)")

    def test_money_type(self):
        sql = translate("CREATE TABLE table ( col MONEY not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col DECIMAL(19, 4) not null)")

    def test_smallmoney_type(self):
        sql = translate("CREATE TABLE table ( col SMALLMONEY not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col DECIMAL(10, 4) not null)")

    def test_tinyint_type(self):
        sql = translate("CREATE TABLE table ( col TINYINT not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col SMALLINT not null)")

    def test_float_type(self):
        sql = translate("CREATE TABLE table ( col FLOAT(@s) not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col FLOAT not null)")

    def test_datetime2_type_with_precision(self):
        sql = translate("CREATE TABLE table ( col DATETIME2(@p) not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col TIMESTAMP not null)")

    def test_datetime2_type(self):
        sql = translate("CREATE TABLE table ( col DATETIME2 not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col TIMESTAMP not null)")

    def test_datetime_type(self):
        sql = translate("CREATE TABLE table ( col DATETIME not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col TIMESTAMP not null)")

    def test_smalldatetime_type(self):
        sql = translate("CREATE TABLE table ( col SMALLDATETIME not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col TIMESTAMP not null)")

    def test_datetimeoffset_type_with_precision(self):
        sql = translate(
            "CREATE TABLE table ( col DATETIMEOFFSET(@p) not null)",
            "redshift",
        )
        assert_sql_equal(sql, "CREATE TABLE table ( col TIMESTAMPTZ not null)")

    def test_datetimeoffset_type(self):
        sql = translate("CREATE TABLE table ( col DATETIMEOFFSET not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col TIMESTAMPTZ not null)")

    def test_text_type(self):
        sql = translate("CREATE TABLE table ( col TEXT not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col VARCHAR(max) not null)")

    def test_ntext_type(self):
        sql = translate("CREATE TABLE table ( col NTEXT not null)", "redshift")
        assert_sql_equal(sql, "CREATE TABLE table ( col VARCHAR(max) not null)")

    def test_uniqueidentifier_type(self):
        sql = translate(
            "CREATE TABLE table ( col UNIQUEIDENTIFIER not null)",
            "redshift",
        )
        assert_sql_equal(sql, "CREATE TABLE table ( col CHAR(36) not null)")

    def test_stdev_pop(self):
        sql = translate("SELECT STDEVP(col) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT STDDEV_POP(col) FROM table")

    def test_var_pop(self):
        sql = translate("SELECT VARP(col) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT VAR_POP(col) FROM table")

    def test_datetime2fromparts(self):
        sql = translate(
            "SELECT DATETIME2FROMPARTS(year,month,day,hour,minute,seconds, 0, 0) FROM table",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(TO_CHAR(year,'0000FM')||'-'||TO_CHAR(month,'00FM')||'-'||TO_CHAR(day,'00FM')||' '||TO_CHAR(hour,'00FM')||':'||TO_CHAR(minute,'00FM')||':'||TO_CHAR(seconds,'00FM') as TIMESTAMP) FROM table",
        )

    def test_datetime2fromparts_with_fractions(self):
        sql = translate(
            "SELECT DATETIME2FROMPARTS(year,month,day,hour,minute,seconds,fractions,precision) FROM table",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(TO_CHAR(year,'0000FM')||'-'||TO_CHAR(month,'00FM')||'-'||TO_CHAR(day,'00FM')||' '||TO_CHAR(hour,'00FM')||':'||TO_CHAR(minute,'00FM')||':'||TO_CHAR(seconds,'00FM')||'.'||TO_CHAR(fractions,repeat('0', precision) || 'FM') as TIMESTAMP) FROM table",
        )

    def test_datetimeoffsetfromparts(self):
        sql = translate(
            "SELECT DATETIMEOFFSETFROMPARTS(year,month,day,hour,minute,seconds, 0,h_offset,m_offset, 0) FROM table",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(TO_CHAR(year,'0000FM')||'-'||TO_CHAR(month,'00FM')||'-'||TO_CHAR(day,'00FM')||' '||TO_CHAR(hour,'00FM')||':'||TO_CHAR(minute,'00FM')||':'||TO_CHAR(seconds,'00FM')||case when h_offset >= 0 then '+' else '-' end ||TO_CHAR(ABS(h_offset),'00FM')||':'||TO_CHAR(ABS(m_offset),'00FM') as TIMESTAMPTZ) FROM table",
        )

    def test_datetimeoffsetfromparts_with_fractions(self):
        sql = translate(
            "SELECT DATETIMEOFFSETFROMPARTS(year,month,day,hour,minute,seconds,fractions,h_offset,m_offset,precision) FROM table",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(TO_CHAR(year,'0000FM')||'-'||TO_CHAR(month,'00FM')||'-'||TO_CHAR(day,'00FM')||' '||TO_CHAR(hour,'00FM')||':'||TO_CHAR(minute,'00FM')||':'||TO_CHAR(seconds,'00FM')||'.'||TO_CHAR(fractions,repeat('0',precision) || 'FM')||case when h_offset >= 0 then '+' else '-' end ||TO_CHAR(ABS(h_offset),'00FM')||':'||TO_CHAR(ABS(m_offset),'00FM') as TIMESTAMPTZ) FROM table",
        )

    def test_getutcdate(self):
        sql = translate("SELECT GETUTCDATE();", "redshift")
        assert_sql_equal(sql, "SELECT CURRENT_TIMESTAMP;")

    def test_smalldatetimefromparts(self):
        sql = translate(
            "SELECT SMALLDATETIMEFROMPARTS(year,month,day,hour,minute) FROM table",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT CAST(TO_CHAR(year,'0000FM')||'-'||TO_CHAR(month,'00FM')||'-'||TO_CHAR(day,'00FM')||' '||TO_CHAR(hour,'00FM')||':'||TO_CHAR(minute,'00FM') as TIMESTAMP) FROM table",
        )

    def test_sysutcdatetime(self):
        sql = translate("SELECT SYSUTCDATETIME();", "redshift")
        assert_sql_equal(sql, "SELECT CURRENT_TIMESTAMP;")

    def test_atn2(self):
        sql = translate("SELECT ATN2(a, b) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT ATAN2(a, b) FROM table")

    def test_truncation_of_number(self):
        sql = translate("SELECT ROUND(expression,length,trunc) FROM table", "redshift")
        assert_sql_equal(
            sql,
            "SELECT case when trunc = 0 then ROUND(CAST(expression AS FLOAT),length) else TRUNC(CAST(expression AS FLOAT),length) end FROM table",
        )

    def test_charindex_from_position(self):
        sql = translate("SELECT CHARINDEX('test',column, 3) FROM table", "redshift")
        assert_sql_equal(
            sql,
            "SELECT case when CHARINDEX('test', SUBSTRING(column, 3)) > 0 then (CHARINDEX('test', SUBSTRING(column, 3)) + 3 - 1) else 0 end FROM table",
        )

    def test_quotename(self):
        sql = translate("SELECT QUOTENAME(a) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT QUOTE_IDENT(a) FROM table")

    def test_space(self):
        sql = translate("SELECT SPACE(n) FROM table", "redshift")
        assert_sql_equal(sql, "SELECT REPEAT(' ',n) FROM table")

    def test_stuff(self):
        sql = translate(
            "SELECT STUFF(expression, start, length, replace) FROM table",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT SUBSTRING(expression, 0, start)|| replace||SUBSTRING(expression, start + length) FROM table",
        )

    def test_concat_seven_args(self):
        sql = translate("SELECT CONCAT(p1,p2,p3,p4,p5,p6,p7) FROM table", "redshift")
        assert_sql_equal(
            sql,
            "SELECT CONCAT(p1,CONCAT(p2,CONCAT(p3,CONCAT(p4,CONCAT(p5,CONCAT(p6,p7)))))) FROM table",
        )

    def test_concat_with_long_string(self):
        sql = translate(
            "SELECT CONCAT('Condition occurrence record observed during long_term_days on or prior to cohort index:  ', CAST((p1.covariate_id-101)/1000 AS VARCHAR), '-', CASE WHEN c1.concept_name IS NOT NULL THEN c1.concept_name ELSE 'Unknown invalid concept' END) FROM table",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT CONCAT('Condition occurrence record observed during long_term_days on or prior to cohort index:  ',CONCAT(CAST((p1.covariate_id-101)/1000 AS VARCHAR),CONCAT('-',CASE WHEN c1.concept_name IS NOT NULL THEN c1.concept_name ELSE 'Unknown invalid concept' END))) FROM table",
        )

    def test_ctas_temp_with_cte_person_id(self):
        sql = translate(
            "WITH a AS b SELECT person_id, col1, col2 INTO #table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  #table \nDISTKEY(person_id)\nAS\nWITH\n a \nAS\n b \nSELECT\n  person_id , col1, col2 \nFROM\n person;",
        )

    def test_ctas_temp_with_cte_person_id_at_end(self):
        sql = translate(
            "WITH a AS b SELECT col1, col2, person_id INTO #table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  #table \nDISTKEY(person_id)\nAS\nWITH\n a \nAS\n b \nSELECT\n  col1, col2, person_id\nFROM\n person;",
        )

    def test_ctas_with_cte_person_id(self):
        sql = translate(
            "WITH a AS b SELECT person_id, col1, col2 INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(person_id)\nAS\nWITH\n a \nAS\n b \nSELECT\n  person_id , col1, col2 \nFROM\n person;",
        )

    def test_ctas_with_cte_person_id_with_alias(self):
        sql = translate(
            "WITH a AS b SELECT person_id as dist, col1, col2 INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(dist)\nAS\nWITH\n a \nAS\n b \nSELECT\n  person_id as dist, col1, col2 \nFROM\n person;",
        )

    def test_ctas_with_cte_person_id_with_alias_at_end(self):
        sql = translate(
            "WITH a AS b SELECT col1, col2, person_id as dist INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(dist)\nAS\nWITH\n a \nAS\n b \nSELECT\n col1, col2, person_id as dist \nFROM\n person;",
        )

    def test_ctas_with_cte_person_id_with_alias_no_as(self):
        sql = translate(
            "WITH a AS b SELECT col1, person_id dist, col2 INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(dist)\nAS\nWITH\n a \nAS\n b \nSELECT\n col1, person_id dist, col2 \nFROM\n person;",
        )

    def test_ctas_with_cte_person_id_with_alias_no_as_at_end(self):
        sql = translate(
            "WITH a AS b SELECT col1, col2, person_id dist INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(dist)\nAS\nWITH\n a \nAS\n b \nSELECT\n col1, col2, person_id dist \nFROM\n person;",
        )

    def test_ctas_temp_person_id(self):
        sql = translate(
            "SELECT person_id, col1, col2 INTO #table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  #table \nDISTKEY(person_id)\nAS\nSELECT\n  person_id , col1, col2 \nFROM\n person;",
        )

    def test_ctas_person_id(self):
        sql = translate(
            "SELECT person_id, col1, col2 INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(person_id)\nAS\nSELECT\n  person_id , col1, col2 \nFROM\n person;",
        )

    def test_ctas_person_id_with_alias(self):
        sql = translate(
            "SELECT person_id as dist, col1, col2 INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(dist)\nAS\nSELECT\n  person_id as dist, col1, col2 \nFROM\n person;",
        )

    def test_ctas_person_id_with_alias_at_end(self):
        sql = translate(
            "SELECT col1, col2, person_id as dist INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(dist)\nAS\nSELECT\n col1, col2, person_id as dist \nFROM\n person;",
        )

    def test_ctas_person_id_with_alias_no_as(self):
        sql = translate(
            "SELECT person_id dist, col1, col2 INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(dist)\nAS\nSELECT\n  person_id dist, col1, col2 \nFROM\n person;",
        )

    def test_ctas_person_id_with_alias_no_as_at_end(self):
        sql = translate(
            "SELECT col1, col2, person_id dist INTO table FROM person;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table \nDISTKEY(dist)\nAS\nSELECT\n col1, col2, person_id dist \nFROM\n person;",
        )

    def test_create_table_person_id(self):
        sql = translate(
            "CREATE TABLE [dbo].[drug_era] ([drug_era_id] bigint NOT NULL, [person_id] bigint NOT NULL, [drug_concept_id] bigint NOT NULL, [drug_era_start_date] date NOT NULL, [drug_era_end_date] date NOT NULL, [drug_exposure_count] int NULL, [gap_days] int NULL);",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  [dbo].[drug_era]  ([drug_era_id] bigint NOT NULL, [person_id] bigint NOT NULL, [drug_concept_id] bigint NOT NULL, [drug_era_start_date] date NOT NULL, [drug_era_end_date] date NOT NULL, [drug_exposure_count] int NULL, [gap_days] int NULL)\nDISTKEY(person_id);",
        )

    def test_isdate(self):
        sql = translate("SELECT * FROM table WHERE ISDATE(col) = 1", "redshift")
        assert_sql_equal(
            sql,
            "SELECT * FROM table WHERE REGEXP_INSTR(col, '^(\\\\d{4}[/\\-]?[01]\\\\d[/\\-]?[0123]\\\\d)([ T]([0-1][0-9]|[2][0-3]):([0-5][0-9])(:[0-5][0-9](.\\\\d+)?)?)?$') = 1",
        )

    def test_isnumeric(self):
        sql = translate("SELECT * FROM table WHERE ISNUMERIC(col) = 1", "redshift")
        assert_sql_equal(
            sql,
            "SELECT * FROM table WHERE REGEXP_INSTR(col, '^[\\-\\+]?(\\\\d*\\\\.)?\\\\d+([Ee][\\-\\+]?\\\\d+)?$') = 1",
        )

    def test_patindex(self):
        sql = translate("SELECT PATINDEX(pattern,expression) FROM table;", "redshift")
        assert_sql_equal(
            sql,
            "SELECT REGEXP_INSTR(expression, case when LEFT(pattern,1)<>'%' and RIGHT(pattern,1)='%' then '^' else '' end||TRIM('%' FROM REPLACE(pattern,'_','.'))||case when LEFT(pattern,1)='%' and RIGHT(pattern,1)<>'%' then '$' else '' end) FROM table;",
        )

    def test_select_into_temp_with_cte_default_hashing(self):
        sql = translate(
            "WITH cte(a1) AS (SELECT a1 FROM table_a) SELECT * INTO #table FROM cte;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  #table  DISTSTYLE ALL\nAS\nWITH\n cte(a1) \nAS\n (SELECT a1 FROM table_a) \nSELECT\n * \nFROM\n cte;",
        )

    def test_select_into_permanent_with_cte_default_hashing(self):
        sql = translate(
            "WITH cte(a1) AS (SELECT a1 FROM table_a) SELECT * INTO table FROM cte;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table  DISTSTYLE ALL\nAS\nWITH\n cte(a1) \nAS\n (SELECT a1 FROM table_a) \nSELECT\n * \nFROM\n cte;",
        )

    def test_select_into_temp_default_hashing(self):
        sql = translate(
            "SELECT * INTO #table FROM another_table;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  #table  DISTSTYLE ALL\nAS\nSELECT\n * \nFROM\n another_table;",
        )

    def test_select_into_permanent_default_hashing(self):
        sql = translate(
            "SELECT * INTO table FROM another_table;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table  DISTSTYLE ALL\nAS\nSELECT\n * \nFROM\n another_table;",
        )

    def test_select_value_into_temp_default_hashing(self):
        sql = translate("SELECT a INTO #table;", "redshift")
        assert_sql_equal(sql, "CREATE TABLE  #table DISTSTYLE ALL\nAS\nSELECT\n a ;")

    def test_select_value_into_permanent_default_hashing(self):
        sql = translate("SELECT a INTO table;", "redshift")
        assert_sql_equal(sql, "CREATE TABLE  table DISTSTYLE ALL\nAS\nSELECT\n a ;")

    def test_create_temp_table_default_hashing(self):
        sql = translate(
            "CREATE TABLE #table (id int not null, col varchar(max));",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  #table  (id int not null, col varchar(max))\nDISTSTYLE ALL;",
        )

    def test_create_permanent_table_default_hashing(self):
        sql = translate(
            "CREATE TABLE table (id int not null, col varchar(max));",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  table  (id int not null, col varchar(max))\nDISTSTYLE ALL;",
        )

    def test_create_table_if_not_exists_with_hashing(self):
        sql = translate(
            "IF OBJECT_ID('dbo.heracles_results', 'U') IS NULL\nCREATE TABLE dbo.heracles_results\n(\ncohort_definition_id int,\nanalysis_id int,\nstratum_1 varchar(255),\nstratum_2 varchar(255),\nstratum_3 varchar(255),\nstratum_4 varchar(255),\nstratum_5 varchar(255),\ncount_value bigint,\nlast_update_time datetime\n);",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "CREATE TABLE  IF NOT EXISTS  dbo.heracles_results\n(cohort_definition_id int,\nanalysis_id  int,\nstratum_1 varchar(255),\nstratum_2 varchar(255),\nstratum_3 varchar(255),\nstratum_4 varchar(255),\nstratum_5 varchar(255),\ncount_value bigint,\nlast_update_time TIMESTAMP\n)\nDISTKEY(analysis_id);",
        )

    def test_distinct_top(self):
        sql = translate("SELECT DISTINCT TOP 100 * FROM table WHERE a = b;", "redshift")
        assert_sql_equal(sql, "SELECT TOP 100 DISTINCT * FROM table WHERE a = b;")

    def test_xor_operator(self):
        sql = translate("select a ^ b from c where a = 1;", "redshift")
        assert_sql_equal(sql, "select a # b from c where a = 1;")

    def test_hint_distkey_sortkey_ctas_cte(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(COMPOUND:start_date)\nWITH cte(row_id, start_date) AS (select * from basetable)\nSELECT * INTO #my_table FROM cte;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(COMPOUND:start_date)\nCREATE TABLE #my_table\nDISTKEY(row_id)\nCOMPOUND SORTKEY(start_date)\nAS\nWITH cte(row_id, start_date) AS (select * from basetable)\nSELECT\n * \nFROM\n cte;",
        )

    def test_hint_sortkey_ctas_cte(self):
        sql = translate(
            "--HINT SORT_ON_KEY(COMPOUND:start_date)\nWITH cte(row_id, start_date) AS (select * from basetable)\nSELECT * INTO #my_table FROM cte;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT SORT_ON_KEY(COMPOUND:start_date)\nCREATE TABLE #my_table\nCOMPOUND SORTKEY(start_date)\nAS\nWITH cte(row_id, start_date) AS (select * from basetable)\nSELECT\n * \nFROM\n cte;",
        )

    def test_hint_distkey_sortkey_ctas(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(:start_date, end_date)\nSELECT * INTO #my_table FROM other_table;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(:start_date, end_date)\nCREATE TABLE #my_table\nDISTKEY(row_id)\nSORTKEY(start_date, end_date)\nAS\nSELECT\n*\nFROM\n other_table;",
        )

    def test_hint_sortkey_ctas(self):
        sql = translate(
            "--HINT SORT_ON_KEY(:start_date, end_date)\nSELECT * INTO #my_table FROM other_table;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT SORT_ON_KEY(:start_date, end_date)\nCREATE TABLE #my_table\nSORTKEY(start_date, end_date)\nAS\nSELECT\n * \nFROM\n other_table;",
        )

    def test_hint_distkey_sortkey_create_table(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(INTERLEAVED:start_date)\nCREATE TABLE cdm.my_table (row_id INT, start_date);",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(INTERLEAVED:start_date)\nCREATE TABLE cdm.my_table (row_id INT, start_date)\nDISTKEY(row_id)\nINTERLEAVED SORTKEY(start_date);",
        )

    def test_hint_sortkey_create_table(self):
        sql = translate(
            "--HINT SORT_ON_KEY(INTERLEAVED:start_date)\nCREATE TABLE cdm.my_table (row_id INT, start_date);",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "--HINT SORT_ON_KEY(INTERLEAVED:start_date)\nCREATE TABLE cdm.my_table (row_id INT, start_date)\nINTERLEAVED SORTKEY(start_date);",
        )

    def test_convert_to_date(self):
        sql = translate("select CONVERT(DATE, start_date) from my_table;", "redshift")
        assert_sql_equal(sql, "select CAST(start_date as DATE) from my_table;")

    def test_convert_to_timestamptz(self):
        sql = translate(
            "select CONVERT(TIMESTAMPTZ, start_date) from my_table;",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select CONVERT(TIMESTAMP WITH TIME ZONE, start_date) from my_table;",
        )

    def test_partition_window_sorted_descending(self):
        sql = translate(
            "select sum(count(person_id)) over (PARTITION BY procedure_concept_id order by prc_cnt desc) as count_value",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select sum(count(person_id)) OVER (PARTITION BY procedure_concept_id  ORDER BY prc_cnt  DESC ROWS UNBOUNDED PRECEDING) as count_value",
        )

    def test_partition_window_sorted_ascending(self):
        sql = translate(
            "select sum(count(person_id)) over (PARTITION BY procedure_concept_id order by prc_cnt asc) as count_value",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select sum(count(person_id)) OVER (PARTITION BY procedure_concept_id  ORDER BY prc_cnt  ASC ROWS UNBOUNDED PRECEDING) as count_value",
        )

    def test_partition_window_no_sort_specified(self):
        sql = translate(
            "select sum(count(person_id)) over (PARTITION BY procedure_concept_id order by prc_cnt) as count_value",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select sum(count(person_id)) OVER (PARTITION BY procedure_concept_id  ORDER BY prc_cnt  ROWS UNBOUNDED PRECEDING) as count_value",
        )

    def test_partition_window_with_specified_frame(self):
        sql = translate(
            "select MAX(start_ordinal) OVER (PARTITION BY groupid ORDER BY event_date, event_type ROWS UNBOUNDED PRECEDING) AS start_ordinal",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select MAX(start_ordinal) OVER (PARTITION BY groupid ORDER BY event_date, event_type ROWS UNBOUNDED PRECEDING) AS start_ordinal",
        )

    def test_partition_window_row_number(self):
        sql = translate(
            "select ROW_NUMBER() over (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select ROW_NUMBER() OVER (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_partition_window_cume_dist(self):
        sql = translate(
            "select CUME_DIST() over (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select CUME_DIST() OVER (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_partition_window_dense_rank(self):
        sql = translate(
            "select DENSE_RANK() over (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select DENSE_RANK() OVER (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_partition_window_percent_rank(self):
        sql = translate(
            "select PERCENT_RANK() over (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select PERCENT_RANK() OVER (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_partition_window_rank(self):
        sql = translate(
            "select RANK() over (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select RANK() OVER (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_partition_window_lag(self):
        sql = translate(
            "select LAG(mycol) over (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select LAG(mycol) OVER (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_partition_window_lead(self):
        sql = translate(
            "select LEAD(mycol) over (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select LEAD(mycol) OVER (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_partition_window_ntile(self):
        sql = translate(
            "select NTILE(4) over (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select NTILE(4) OVER (PARTITION BY procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_window_sorted_descending_no_partition(self):
        sql = translate(
            "select sum(count(person_id)) over (order by prc_cnt desc) as count_value",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select sum(count(person_id)) OVER (ORDER BY prc_cnt  DESC ROWS UNBOUNDED PRECEDING) as count_value",
        )

    def test_window_sorted_ascending_no_partition(self):
        sql = translate(
            "select sum(count(person_id)) over (order by prc_cnt asc) as count_value",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select sum(count(person_id)) OVER (ORDER BY prc_cnt  ASC ROWS UNBOUNDED PRECEDING) as count_value",
        )

    def test_window_no_sort_no_partition(self):
        sql = translate(
            "select sum(count(person_id)) over (order by prc_cnt) as count_value",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select sum(count(person_id)) OVER (ORDER BY prc_cnt ROWS UNBOUNDED PRECEDING) as count_value",
        )

    def test_window_row_number_no_partition(self):
        sql = translate(
            "select ROW_NUMBER() over (procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select ROW_NUMBER() OVER (procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_window_cume_dist_no_partition(self):
        sql = translate(
            "select CUME_DIST() over (procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select CUME_DIST() OVER (procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_window_dense_rank_no_partition(self):
        sql = translate(
            "select DENSE_RANK() over (procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select DENSE_RANK() OVER (procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_window_percent_rank_no_partition(self):
        sql = translate(
            "select PERCENT_RANK() over (procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select PERCENT_RANK() OVER (procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_window_rank_no_partition(self):
        sql = translate(
            "select RANK() over (procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select RANK() OVER (procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_window_lag_no_partition(self):
        sql = translate(
            "select LAG(mycol) over (procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select LAG(mycol) OVER (procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_window_lead_no_partition(self):
        sql = translate(
            "select LEAD(mycol) over (procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select LEAD(mycol) OVER (procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_window_ntile_no_partition(self):
        sql = translate(
            "select NTILE(4) over (procedure_concept_id ORDER BY prc_cnt) as num",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "select NTILE(4) OVER (procedure_concept_id ORDER BY prc_cnt) as num",
        )

    def test_clustered_index_not_supported(self):
        sql = translate(
            "CREATE CLUSTERED INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "redshift",
        )
        assert_sql_equal(sql, "-- redshift does not support indexes")

    def test_index_not_supported(self):
        sql = translate(
            "CREATE INDEX idx_raw_4000 ON #raw_4000 (cohort_definition_id, subject_id, op_start_date);",
            "redshift",
        )
        assert_sql_equal(sql, "-- redshift does not support indexes")

    def test_analyze_table(self):
        sql = translate("UPDATE STATISTICS results_schema.heracles_results;", "redshift")
        assert_sql_equal(sql, "ANALYZE results_schema.heracles_results;")

    def test_datetime_and_datetime2(self):
        sql = translate("CREATE TABLE x (a DATETIME2, b DATETIME);", "redshift")
        assert_sql_equal(sql, "CREATE TABLE x  (a TIMESTAMP, b TIMESTAMP)\nDISTSTYLE ALL;")

    def test_drop_table_if_exists(self):
        sql = translate("DROP TABLE IF EXISTS test;", "redshift")
        assert_sql_equal(sql, "DROP TABLE IF EXISTS test;")

    def test_drvd(self):
        sql = translate(
            "SELECT\n      TRY_CAST(name AS VARCHAR(MAX)) AS name,\n      TRY_CAST(speed AS FLOAT) AS speed\n    FROM (  VALUES ('A', 1.0), ('B', 2.0)) AS drvd(name, speed);",
            "redshift",
        )
        assert_sql_equal(
            sql,
            "SELECT\n      CAST(name AS VARCHAR(MAX)) AS name,\n      CAST(speed AS FLOAT) AS speed\n    FROM (SELECT NULL AS name, NULL AS speed WHERE (0 = 1) UNION ALL SELECT 'A', 1.0 UNION ALL SELECT 'B', 2.0) AS values_table;",
        )
