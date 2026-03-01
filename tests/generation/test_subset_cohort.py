from __future__ import annotations

from circe.api import generate_cohort, generate_subset
from circe.generation import GenerationConfig
from circe.generation.subsets.definitions import CohortSubsetOperator, SubsetDefinition

from tests.generation.conftest import make_expression, seed_base_tables


def test_cohort_subset_intersect(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=3)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=300,
        config=config,
        policy="replace",
    )

    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 3],
                "condition_occurrence_id": [9001, 9003],
                "condition_concept_id": [222, 222],
                "condition_start_date": ["2020-01-01", "2020-01-01"],
                "condition_end_date": ["2020-01-01", "2020-01-01"],
            }
        ),
        overwrite=True,
    )
    _ = generate_cohort(
        make_expression(222),
        backend=conn,
        cohort_id=301,
        config=config,
        policy="replace",
    )

    definition = SubsetDefinition(
        subset_name="intersect-with-301",
        parent_cohort_id=300,
        operators=(
            CohortSubsetOperator(
                subset_cohort_id=301,
                relationship="intersect",
                target_anchor="start",
                subset_anchor="start",
                window_start_offset=-1,
                window_end_offset=1,
            ),
        ),
    )

    status = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=302,
        config=config,
        policy="replace",
    )
    assert status.status in {"generated", "replaced"}

    table = conn.table("cohort", database="main")
    result = table.filter(table.cohort_definition_id == 302).execute()
    assert set(result.subject_id) == {1, 3}


def test_cohort_subset_exclude(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=2)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=310,
        config=config,
        policy="replace",
    )

    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [2],
                "condition_occurrence_id": [9992],
                "condition_concept_id": [333],
                "condition_start_date": ["2020-01-01"],
                "condition_end_date": ["2020-01-01"],
            }
        ),
        overwrite=True,
    )
    _ = generate_cohort(
        make_expression(333),
        backend=conn,
        cohort_id=311,
        config=config,
        policy="replace",
    )

    definition = SubsetDefinition(
        subset_name="exclude-311",
        parent_cohort_id=310,
        operators=(
            CohortSubsetOperator(
                subset_cohort_id=311,
                relationship="exclude",
                target_anchor="start",
                subset_anchor="start",
                window_start_offset=-1,
                window_end_offset=1,
            ),
        ),
    )

    status = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=312,
        config=config,
        policy="replace",
    )
    assert status.status in {"generated", "replaced"}

    table = conn.table("cohort", database="main")
    result = table.filter(table.cohort_definition_id == 312).execute()
    assert set(result.subject_id) == {1}
