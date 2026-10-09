"""Test Synapse translation - ported from OHDSI SqlRender test-translate-synapse.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestSynapseTranslation:
    def test_create_table_with_constraint_default_1(self):
        sql = translate(
            "CREATE TABLE a(c1 DATETIME CONSTRAINT a_c1_def DEFAULT GETDATE());",
            "synapse",
        )
        assert_sql_equal(sql, "CREATE TABLE a(c1 DATETIME);")

    def test_create_table_with_constraint_default_2(self):
        sql = translate("CREATE TABLE a(c1 DATETIME DEFAULT GETDATE());", "synapse")
        assert_sql_equal(sql, "CREATE TABLE a(c1 DATETIME);")

    def test_create_index_with_where(self):
        sql = translate("CREATE INDEX idx_a ON a(c1, c2) WHERE c3 <> '';", "synapse")
        assert_sql_equal(sql, "CREATE INDEX idx_a ON a(c1, c2);")

    def test_iif(self):
        sql = translate("SELECT IIF(a>b, 1, b) AS max_val FROM table;", "synapse")
        assert_sql_equal(sql, "SELECT CASE WHEN a>b THEN 1 ELSE b END AS max_val FROM table ;")

    def test_drop_table_if_exists_temp(self):
        sql = translate("DROP TABLE IF EXISTS #my_temp;", "synapse")
        assert_sql_equal(
            sql,
            "IF OBJECT_ID('tempdb..#my_temp', 'U') IS NOT NULL DROP TABLE #my_temp;",
        )

    def test_drop_table_if_exists(self):
        sql = translate("DROP TABLE IF EXISTS cdm.dbo.table;", "synapse")
        assert_sql_equal(
            sql,
            "IF OBJECT_ID('cdm.dbo.table', 'U') IS NOT NULL DROP TABLE cdm.dbo.table;",
        )

    def test_create_table_if_not_exists(self):
        sql = translate("CREATE TABLE IF NOT EXISTS cdm.dbo.table (x INT);", "synapse")
        assert_sql_equal(
            sql,
            "IF OBJECT_ID('cdm.dbo.table ', 'U') IS NULL CREATE TABLE cdm.dbo.table (x INT);",
        )
