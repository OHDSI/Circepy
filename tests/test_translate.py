import pytest
from circe.sqlrender.render import render_sql, translate_sql

@pytest.fixture
def simple_template():
    template = "SELECT @column FROM @cdm_schema.table"
    params = {"column": "person_id", "cdm_schema": "cdm"}
    return template, params

def test_render_sql_spark(simple_template):
    template, params = simple_template
    sql = render_sql(template, params, dialect="spark")
    # Spark dialect uses backticks for identifiers
    assert "`cdm`" in sql or "`cdm`" in sql.lower()
    assert "`person_id`" not in sql  # column is a value, not quoted identifier

def test_translate_to_postgres(simple_template):
    template, params = simple_template
    sql_spark = render_sql(template, params, dialect="spark")
    sql_pg = translate_sql(sql_spark, "postgres")
    # Postgres uses double quotes for identifiers
    assert '"cdm"' in sql_pg
    # Ensure no backticks remain
    assert '`' not in sql_pg

def test_translate_to_redshift(simple_template):
    template, params = simple_template
    sql_spark = render_sql(template, params, dialect="spark")
    sql_rs = translate_sql(sql_spark, "redshift")
    assert '"cdm"' in sql_rs
    assert '`' not in sql_rs

def test_translate_to_snowflake(simple_template):
    template, params = simple_template
    sql_spark = render_sql(template, params, dialect="spark")
    sql_sf = translate_sql(sql_spark, "snowflake")
    assert '"cdm"' in sql_sf
    assert '`' not in sql_sf
