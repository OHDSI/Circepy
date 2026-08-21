"""Test SQL splitting - ported from OHDSI SqlRender test-splitSql.R"""

from circe.sqlrender import split_sql


class TestSplitSql:
    def test_split_simple_statements(self):
        parts = split_sql("SELECT * INTO a FROM b; USE x; DROP TABLE c;")
        assert parts == ["SELECT * INTO a FROM b", "USE x", "DROP TABLE c"]

    def test_split_with_begin_end(self):
        parts = split_sql("BEGIN\nSELECT * INTO a FROM b;\nEND;\nUSE x;")
        assert parts == ["BEGIN\nSELECT * INTO a FROM b;\nEND;", "USE x"]

    def test_split_with_case_end(self):
        parts = split_sql("SELECT CASE WHEN x=1 THEN 0 ELSE 1 END AS x INTO a FROM b;\nUSE x;")
        assert parts == [
            "SELECT CASE WHEN x=1 THEN 0 ELSE 1 END AS x INTO a FROM b",
            "USE x",
        ]

    def test_split_with_end_in_quoted_text(self):
        parts = split_sql("insert into a (x) values ('end');\n insert into a (x) values ('begin');")
        assert parts == [
            "insert into a (x) values ('end')",
            "insert into a (x) values ('begin')",
        ]

    def test_split_with_case_end_at_end(self):
        sql = "SELECT CASE WHEN x=1 THEN 0 ELSE 1 END FROM a GROUP BY CASE WHEN x=1 THEN 0 ELSE 1 END;"
        parts = split_sql(sql)
        assert parts == [
            "SELECT CASE WHEN x=1 THEN 0 ELSE 1 END FROM a GROUP BY CASE WHEN x=1 THEN 0 ELSE 1 END"
        ]

    def test_split_with_reserved_word_end_as_field(self):
        sql = "INSERT INTO t (data_source, start, [end]) VALUES ('hes', '1990-01-01', '2014-12-31');"
        parts = split_sql(sql)
        assert parts == [
            "INSERT INTO t (data_source, start, [end]) VALUES ('hes', '1990-01-01', '2014-12-31')"
        ]

    def test_split_with_comment_last_line_no_eol(self):
        parts = split_sql("SELECT * FROM table;\n-- end")
        assert parts == ["SELECT * FROM table"]

    def test_split_with_hint_at_start(self):
        parts = split_sql("--HINT DISTRIBUTE_ON_KEY(analysis_id)\nCREATE TABLE results.achilles_results_dist")
        assert parts == ["--HINT DISTRIBUTE_ON_KEY(analysis_id)\nCREATE TABLE results.achilles_results_dist"]

    def test_split_with_hint_in_second_statement(self):
        parts = split_sql(
            "DROP TABLE blah;\n--HINT DISTRIBUTE_ON_KEY(analysis_id)\nCREATE TABLE results.achilles_results_dist;"
        )
        assert parts == [
            "DROP TABLE blah",
            "--HINT DISTRIBUTE_ON_KEY(analysis_id)\nCREATE TABLE results.achilles_results_dist",
        ]

    def test_split_single_statement_no_semicolon(self):
        parts = split_sql("SELECT * FROM table")
        assert parts == ["SELECT * FROM table"]
