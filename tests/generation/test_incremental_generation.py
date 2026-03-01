from __future__ import annotations

from circe.api import generate_cohort, generate_cohort_set
from circe.generation import GenerationConfig, GenerationTarget

from tests.generation.conftest import make_expression, seed_base_tables


def test_generate_cohort_set_changed_only_skips_unchanged(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=1)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    targets = [GenerationTarget(cohort_id=99, expression=make_expression(111))]

    _ = generate_cohort_set(
        targets,
        backend=conn,
        config=config,
        policy="replace",
    )

    second = generate_cohort_set(
        targets,
        backend=conn,
        config=config,
        policy="replace_if_changed",
        changed_only=True,
    )
    assert second.total == 1
    assert second.skipped == 1


def test_replace_if_changed_ignores_source_data_changes_by_default(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=1)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    first = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=120,
        config=config,
        policy="replace",
    )
    assert first.status in {"generated", "replaced"}

    seed_base_tables(ibis, conn, concept_id=111, rows=3)
    second = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=120,
        config=config,
        policy="replace_if_changed",
    )
    assert second.status == "skipped"


def test_replace_if_changed_honors_data_version_token(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=1)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=121,
        config=config,
        policy="replace",
        data_version_token="etl-v1",
    )

    seed_base_tables(ibis, conn, concept_id=111, rows=3)
    second = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=121,
        config=config,
        policy="replace_if_changed",
        data_version_token="etl-v2",
    )
    assert second.status in {"generated", "replaced"}
