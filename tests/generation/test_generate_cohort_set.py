from __future__ import annotations

from circe.api import generate_cohort_set
from circe.generation import GenerationConfig, GenerationTarget

from tests.generation.conftest import make_expression, seed_base_tables


def test_generate_cohort_set_mixed_statuses(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=2)

    config = GenerationConfig(cdm_schema="main", results_schema="main")

    targets = [
        GenerationTarget(cohort_id=1, expression=make_expression(111), cohort_name="A"),
        GenerationTarget(cohort_id=2, expression=make_expression(111), cohort_name="B"),
    ]

    first = generate_cohort_set(
        targets,
        backend=conn,
        config=config,
        policy="replace",
    )
    assert first.total == 2
    assert first.generated + first.replaced == 2

    second = generate_cohort_set(
        targets,
        backend=conn,
        config=config,
        policy="replace_if_changed",
    )
    assert second.total == 2
    assert second.skipped == 2


def test_generate_cohort_set_filters(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=2)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    targets = [
        GenerationTarget(cohort_id=1, expression=make_expression(111), cohort_name="A"),
        GenerationTarget(cohort_id=2, expression=make_expression(111), cohort_name="B"),
        GenerationTarget(cohort_id=3, expression=make_expression(111), cohort_name="C"),
    ]

    filtered = generate_cohort_set(
        targets,
        backend=conn,
        config=config,
        policy="replace",
        cohort_ids={1, 3},
        cohort_names={"A", "C"},
    )
    assert filtered.total == 2
    ids = {status.cohort_id for status in filtered.statuses}
    assert ids == {1, 3}
