import pytest
from circe.sqlrender.render import render_sql, translate_sql

def test_render_sql_basic():
    template = "SELECT * FROM @cdm_schema.person WHERE person_id = @id"
    params = {"cdm_schema": "my_cdm", "id": 123}
    rendered = render_sql(template, params)
    
    # Check that placeholders are replaced
    assert "my_cdm" in rendered
    assert "123" in rendered
    assert "@cdm_schema" not in rendered
    assert "@id" not in rendered

def test_render_sql_missing_param():
    template = "SELECT * FROM @missing"
    params = {"test": 1}
    rendered = render_sql(template, params)
    assert "@missing" in rendered

def test_render_sql_no_automatic_formatting():
    # Test that render_sql does NOT automatically format/transpile anymore
    # to avoid issues with temp tables before the translation step.
    template = "select * from table where x=@x"
    params = {"x": 1}
    rendered = render_sql(template, params)
    assert rendered == "select * from table where x=1"

def test_translate_sql_basic():
    # T-SQL (MS SQL Server) to Postgres translation
    sql_tsql = "SELECT TOP 10 * FROM my_db.my_table"
    sql_pg = translate_sql(sql_tsql, target_dialect="postgres", source_dialect="tsql")
    
    # Postgres uses double quotes for identifiers if needed, and LIMIT is supported
    # (Actually limit is the same, but let's check for identifier quoting if it was needed)
    assert "SELECT" in sql_pg
    assert "LIMIT 10" in sql_pg

def test_translate_sql_complex():
    # Test something that differs between dialects
    # T-SQL: `DATEADD` and `DATEDIFF`
    # sqlglot handles these
    sql_tsql = "SELECT DATEDIFF(day, '2023-01-01', '2023-01-10')"
    sql_pg = translate_sql(sql_tsql, target_dialect="postgres", source_dialect="tsql")
    
    # Postgres doesn't have a DATEDIFF(unit, ...) function like Spark
    # It usually uses (date1 - date2)
    assert "DATEDIFF" not in sql_pg.upper()
    assert "2023-01-10" in sql_pg
    assert "2023-01-01" in sql_pg

def test_render_sql_conditional():
    template = "SELECT * FROM table { @val == 1 }?{ WHERE x = 1 } : { WHERE x = 0 }"
    
    params = {"val": 1}
    rendered_true = render_sql(template, params)
    assert "WHERE x = 1" in rendered_true
    assert "WHERE x = 0" not in rendered_true
    
    params = {"val": 0}
    rendered_false = render_sql(template, params)
    assert "WHERE x = 0" in rendered_false
    assert "WHERE x = 1" not in rendered_false

def test_render_sql_conditional_simple():
    template = "{ 1 == 1 }?{ TRUE_BLOCK }"
    rendered = render_sql(template, {})
    assert "TRUE_BLOCK" in rendered
    assert "?" not in rendered

def test_translate_sql_temp_emulation():
    sql = "CREATE TABLE #Codesets (codeset_id int); SELECT * FROM #Codesets"
    
    # Translate with temp emulation
    translated = translate_sql(
        sql, 
        target_dialect="postgres", 
        temp_emulation_schema="my_temp",
        temp_emulation_prefix="test_prefix_"
    )
    
    # Check that temp tables are rewritten
    # sqlglot might quote identifiers or uppercase them depending on the dialect
    assert "my_temp.test_prefix_codesets" in translated.lower()
    assert "TEMPORARY" not in translated.upper()
    
    # Verify random prefix works
    translated_rnd = translate_sql(
        sql, 
        target_dialect="postgres", 
        temp_emulation_schema="my_temp"
    )
    import re
    # Match something like my_temp.tmp_abcdef12_codesets
    match = re.search(r"my_temp\.tmp_[a-z0-9]{8}_codesets", translated_rnd.lower())
    assert match is not None

def test_translate_sql_multi_statement():
    sql = "SELECT 1; SELECT 2; SELECT 3"
    translated = translate_sql(sql, target_dialect="postgres")
    
    # SHould have semicolons
    assert translated.count(";") >= 3
    assert "SELECT 1;" in translated
    assert "SELECT 2;" in translated
    assert translated.strip().endswith(";")

def test_translate_sql_comment_removal():
    sql = "-- This is a comment\nSELECT 1 /* block \n comment */"
    translated = translate_sql(sql, target_dialect="postgres")
    assert "comment" not in translated
    assert "SELECT 1" in translated

def test_translate_sql_short_circuit():
    # T-SQL to T-SQL should return the string (after comment removal)
    sql = "-- Comment\nSELECT TOP 10 * FROM table"
    translated = translate_sql(sql, target_dialect="tsql")
    # It should NOT be transpiled (which might change TOP 10 to something else or uppercase it)
    # But it SHOULD have comments removed
    assert "Comment" not in translated
    assert "SELECT TOP 10" in translated
