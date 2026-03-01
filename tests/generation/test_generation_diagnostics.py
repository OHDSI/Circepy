from __future__ import annotations

from circe.api import (
    generate_cohort,
    get_generated_cohort_counts,
    validate_generated_cohort,
)
from circe.generation import GenerationConfig

from tests.generation.conftest import make_expression, seed_base_tables, seed_generated_cohort_table


def test_generated_cohort_counts(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=2)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=500,
        config=config,
        policy="replace",
    )

    counts = get_generated_cohort_counts(
        backend=conn,
        cohort_id=500,
        config=config,
    )
    assert counts.row_count == 2
    assert counts.distinct_subject_count == 2
    assert counts.min_start_date is not None
    assert counts.max_end_date is not None


def test_validate_generated_cohort_reports_errors(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_generated_cohort_table(
        ibis,
        conn,
        rows=[
            {
                "cohort_definition_id": 600,
                "subject_id": 1,
                "cohort_start_date": "2020-02-10",
                "cohort_end_date": "2020-02-01",
            }
        ],
        table_name="cohort",
        schema="main",
    )

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    result = validate_generated_cohort(
        backend=conn,
        cohort_id=600,
        config=config,
    )

    assert result.is_valid is False
    assert any("before cohort_start_date" in msg for msg in result.errors)
