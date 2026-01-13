import pytest
from pathlib import Path
from circe.api import cohort_expression_from_json, build_cohort_query
from circe.cohortdefinition import BuildExpressionQueryOptions
from circe.sqlrender import render_sql, translate_sql

COHORTS_DIR = Path(__file__).parent / 'cohorts'
EXAMPLE_COHORTS = ['20854.json', '22008.json']
TARGET_DIALECTS = ['postgres', 'bigquery', 'redshift', 'snowflake']

@pytest.mark.parametrize('cohort_name', EXAMPLE_COHORTS)
@pytest.mark.parametrize('target_dialect', TARGET_DIALECTS)
def test_cohort_translation(cohort_name, target_dialect):
    cohort_path = COHORTS_DIR / cohort_name
    if not cohort_path.exists():
        pytest.skip(f"Cohort {cohort_name} not found")
        
    json_str = cohort_path.read_text()
    expression = cohort_expression_from_json(json_str)
    
    options = BuildExpressionQueryOptions()
    options.generate_stats = True
    
    # 1. Build
    sql_base = build_cohort_query(expression, options)
    
    # 2. Render (resolve OHDSI specific bits)
    dummy_params = {
        "cdm_database_schema": "cdm",
        "vocabulary_database_schema": "vocab",
        "results_database_schema": "results",
        "target_database_schema": "target",
        "target_cohort_table": "cohort",
        "target_cohort_id": 1,
        "cohort_id_field_name": "cohort_definition_id",
        "eraconstructorpad": 0
    }
    sql_rendered = render_sql(sql_base, dummy_params)
    
    # 3. Translate
    sql_translated = translate_sql(sql_rendered, target_dialect=target_dialect)
    
    # Basic assertions
    assert sql_translated is not None
    assert len(sql_translated) > 100
    
    # Check for absence of OHDSI-specific markers in translated SQL
    assert "@cdm_database_schema" not in sql_translated
    assert "{" not in sql_translated
    assert "}" not in sql_translated
    assert "?" not in sql_translated
    
    # Dialect specific checks
    if target_dialect == 'postgres':
        assert 'TEMPORARY TABLE' in sql_translated.upper()
    elif target_dialect == 'bigquery':
        # BigQuery uses different temp table mechanisms or sqlglot handles it
        pass
