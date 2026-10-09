"""Test PDW translation - ported from OHDSI SqlRender test-translate-pdw.R"""

from circe.sqlrender import translate
from tests.sqlrender_utils import assert_sql_equal


class TestPdwTranslation:
    def test_with_select_into(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO d FROM cte1;",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE d WITH (DISTRIBUTION = REPLICATE)\nAS\nWITH cte1 AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1;",
        )

    def test_with_select_into_temp(self):
        sql = translate(
            "WITH cte1 AS (SELECT a FROM b) SELECT c INTO #d FROM cte1;",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE  #d   WITH (LOCATION = USER_DB, DISTRIBUTION = REPLICATE) AS\nWITH cte1 AS (SELECT a FROM b)  SELECT\nc \nFROM\ncte1;",
        )

    def test_create_temp_table(self):
        sql = translate("CREATE TABLE #a (x int);", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE #a (x int)\nWITH (LOCATION = USER_DB, DISTRIBUTION = REPLICATE);",
        )

    def test_create_temp_table_person_id(self):
        sql = translate("CREATE TABLE #a (person_id int);", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE #a ( person_id int)\nWITH (LOCATION = USER_DB, DISTRIBUTION = HASH(person_id));",
        )

    def test_create_temp_table_subject_id(self):
        sql = translate("CREATE TABLE #a (subject_id int);", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE #a ( subject_id int)\nWITH (LOCATION = USER_DB, DISTRIBUTION = HASH(subject_id));",
        )

    def test_create_temp_table_analysis_id(self):
        sql = translate("CREATE TABLE #a (analysis_id int);", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE #a ( analysis_id int)\nWITH (LOCATION = USER_DB, DISTRIBUTION = HASH(analysis_id));",
        )

    def test_create_permanent_table(self):
        sql = translate("CREATE TABLE a (x int);", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE a (x int)\nWITH (DISTRIBUTION = REPLICATE);",
        )

    def test_create_permanent_table_person_id(self):
        sql = translate("CREATE TABLE a (person_id int);", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE a ( person_id int)\nWITH (DISTRIBUTION = HASH(person_id));",
        )

    def test_create_permanent_table_subject_id(self):
        sql = translate("CREATE TABLE a (subject_id int);", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE a ( subject_id int)\nWITH (DISTRIBUTION = HASH(subject_id));",
        )

    def test_create_permanent_table_analysis_id(self):
        sql = translate("CREATE TABLE a (analysis_id int);", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE a ( analysis_id int)\nWITH (DISTRIBUTION = HASH(analysis_id));",
        )

    def test_select_into_permanent(self):
        sql = translate("SELECT a INTO b FROM c WHERE a = 1;", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE b WITH (DISTRIBUTION = REPLICATE)\nAS\nSELECT\n a \nFROM\n c WHERE a = 1;",
        )

    def test_select_into_permanent_person_id(self):
        sql = translate("SELECT a, person_id, b INTO b FROM c WHERE a = 1;", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE b WITH (DISTRIBUTION = HASH(person_id))\nAS\nSELECT\n a, person_id, b \nFROM\n c WHERE a = 1;",
        )

    def test_select_into_permanent_analysis_id(self):
        sql = translate("SELECT a, analysis_id, b INTO b FROM c WHERE a = 1;", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE b WITH (DISTRIBUTION = HASH(analysis_id))\nAS\nSELECT\n a, analysis_id, b \nFROM\n c WHERE a = 1;",
        )

    def test_create_table_constraint_default(self):
        sql = translate(
            "CREATE TABLE a(c1 DATETIME CONSTRAINT a_c1_def DEFAULT GETDATE());",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE a (c1 DATETIME)\nWITH (DISTRIBUTION = REPLICATE);",
        )

    def test_create_table_default(self):
        sql = translate("CREATE TABLE a(c1 DATETIME DEFAULT GETDATE());", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE a (c1 DATETIME)\nWITH (DISTRIBUTION = REPLICATE);",
        )

    def test_create_index_with_where(self):
        sql = translate("CREATE INDEX idx_a ON a(c1, c2) WHERE c3 <> '';", "pdw")
        assert_sql_equal(sql, "CREATE INDEX idx_a ON a(c1, c2);")

    def test_cte_with_preceding_with_in_quotes(self):
        sql = translate(
            "insert into x (a) values ('with'); with cte (a) as(select a from b) select a INTO #c from cte;",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "insert into x (a) values ('with'); IF XACT_STATE() = 1 COMMIT; CREATE TABLE #c WITH (LOCATION = USER_DB, DISTRIBUTION = REPLICATE) AS\nWITH cte (a) AS (select a from b) SELECT\n a \nFROM\n cte;",
        )

    def test_select_into_issue(self):
        sql = translate("SELECT @c1 INTO table FROM @c2 WHERE a = 1;", "pdw")
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE table WITH (DISTRIBUTION = REPLICATE)\nAS\nSELECT\n @c1 \nFROM\n @c2 WHERE a = 1;",
        )

    def test_hint_distribute_on_key_select_into(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id)\nSELECT * INTO #my_table FROM other_table;",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id)\nIF XACT_STATE() = 1 COMMIT; CREATE TABLE #my_table WITH (LOCATION = USER_DB, DISTRIBUTION = HASH(row_id)) AS\nSELECT\n * \nFROM\n other_table;",
        )

    def test_hint_distribute_on_key_create_table(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id)\nCREATE TABLE(row_id INT);",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id)\nIF XACT_STATE() = 1 COMMIT; CREATE TABLE (row_id INT)\nWITH (DISTRIBUTION = HASH(row_id));",
        )

    def test_hint_distribute_on_random_select_into(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_RANDOM\nSELECT * INTO #my_table FROM other_table;",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_RANDOM\nIF XACT_STATE() = 1 COMMIT; CREATE TABLE #my_table WITH (LOCATION = USER_DB, DISTRIBUTION = ROUND_ROBIN) AS\nSELECT\n * \nFROM\n other_table;",
        )

    def test_hint_distribute_on_random_create_table(self):
        sql = translate("--HINT DISTRIBUTE_ON_RANDOM\nCREATE TABLE(row_id INT);", "pdw")
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_RANDOM\nIF XACT_STATE() = 1 COMMIT; CREATE TABLE (row_id INT)\nWITH (DISTRIBUTION = ROUND_ROBIN);",
        )

    def test_create_table_person_id(self):
        sql = translate(
            "CREATE TABLE [dbo].[drug_era] ([drug_era_id] bigint NOT NULL, [person_id] bigint NOT NULL, [drug_concept_id] bigint NOT NULL, [drug_era_start_date] date NOT NULL, [drug_era_end_date] date NOT NULL, [drug_exposure_count] int NULL, [gap_days] int NULL);",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; CREATE TABLE   [dbo].[drug_era]  ([drug_era_id] bigint NOT NULL, [person_id] bigint NOT NULL, [drug_concept_id] bigint NOT NULL, [drug_era_start_date] date NOT NULL, [drug_era_end_date] date NOT NULL, [drug_exposure_count] int NULL, [gap_days] int NULL)\nWITH (DISTRIBUTION = HASH(person_id));",
        )

    def test_hint_distkey_sortkey_create_table(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(start_date)\nCREATE TABLE my_table (row_id INT, start_date DATE);",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(start_date)\nIF XACT_STATE() = 1 COMMIT; CREATE TABLE my_table (row_id INT, start_date DATE)\nWITH (DISTRIBUTION = HASH(row_id));",
        )

    def test_hint_distkey_sortkey_ctas(self):
        sql = translate(
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(start_date)\nSELECT * INTO #my_table FROM other_table;",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "--HINT DISTRIBUTE_ON_KEY(row_id) SORT_ON_KEY(start_date)\nIF XACT_STATE() = 1 COMMIT; CREATE TABLE #my_table WITH (LOCATION = USER_DB, DISTRIBUTION = HASH(row_id)) AS\nSELECT\n * \nFROM\n other_table;",
        )

    def test_create_table_if_not_exists(self):
        sql = translate(
            "IF OBJECT_ID('test.testing', 'U') IS NULL create table test.testing (id int);",
            "pdw",
        )
        assert_sql_equal(
            sql,
            "IF XACT_STATE() = 1 COMMIT; IF OBJECT_ID('test.testing', 'U') IS NULL  CREATE TABLE  test.testing  (id int)\nWITH (DISTRIBUTION = REPLICATE);",
        )
