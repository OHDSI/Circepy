"""Test SQL Server translation - ported from OHDSI SqlRender test-translate-sql_server.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestSqlServerTranslation:
    def test_drop_table_if_exists_temp(self):
        sql = translate("DROP TABLE IF EXISTS #my_temp;", "sql server")
        assert_sql_equal(
            sql,
            "IF OBJECT_ID('tempdb..#my_temp', 'U') IS NOT NULL DROP TABLE #my_temp;",
        )

    def test_drop_table_if_exists(self):
        sql = translate("DROP TABLE IF EXISTS cdm.dbo.table;", "sql server")
        assert_sql_equal(
            sql,
            "IF OBJECT_ID('cdm.dbo.table', 'U') IS NOT NULL DROP TABLE cdm.dbo.table;",
        )

    def test_create_table_if_not_exists(self):
        sql = translate("CREATE TABLE IF NOT EXISTS cdm.dbo.table (x INT);", "sql server")
        assert_sql_equal(
            sql,
            "IF OBJECT_ID('cdm.dbo.table ', 'U') IS NULL CREATE TABLE cdm.dbo.table (x INT);",
        )

    def test_temp_dplyr_dots_pattern(self):
        sql = translate(
            "SELECT * FROM cdm.dbo.my_table AS cdm.dbo.my_table...1;",
            "sql server",
        )
        assert_sql_equal(
            sql,
            "SELECT * FROM cdm.dbo.my_table AS cdmxdboxmy_tablexxx1;",
        )
