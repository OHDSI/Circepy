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
    # Spark to Postgres translation
    sql_spark = "SELECT * FROM my_db.my_table LIMIT 10"
    sql_pg = translate_sql(sql_spark, target_dialect="postgres", source_dialect="spark")
    
    # Postgres uses double quotes for identifiers if needed, and LIMIT is supported
    # (Actually limit is the same, but let's check for identifier quoting if it was needed)
    assert "SELECT" in sql_pg
    assert "LIMIT 10" in sql_pg

def test_translate_sql_complex():
    # Test something that differs between dialects
    # Spark: `DATEDIFF(end, start)` returns days
    # Postgres: `end - start` or `age` or `date_part`
    # sqlglot handles many of these
    sql_spark = "SELECT DATEDIFF(day, '2023-01-01', '2023-01-10')"
    sql_pg = translate_sql(sql_spark, target_dialect="postgres", source_dialect="spark")
    
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
