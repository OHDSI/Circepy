from __future__ import annotations

from circe.api import generate_cohort, generate_subset
from circe.generation import GenerationConfig
from circe.generation.subsets.definitions import CohortSubsetOperator, SubsetDefinition

from tests.generation.conftest import make_expression, seed_base_tables


def test_subset_regenerates_when_parent_checksum_changes(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=1)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=400,
        config=config,
        policy="replace",
    )

    definition = SubsetDefinition(
        subset_name="all-parent",
        parent_cohort_id=400,
        operators=(),
    )

    first = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=401,
        config=config,
        policy="replace",
    )
    assert first.status in {"generated", "replaced"}

    skipped = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=401,
        config=config,
        policy="replace_if_changed",
    )
    assert skipped.status == "skipped"

    seed_base_tables(ibis, conn, concept_id=222, rows=1)
    _ = generate_cohort(
        make_expression(222),
        backend=conn,
        cohort_id=400,
        config=config,
        policy="replace_if_changed",
    )

    regenerated = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=401,
        config=config,
        policy="replace_if_changed",
    )
    assert regenerated.status in {"generated", "replaced"}


def test_subset_regenerates_when_referenced_cohort_changes(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=2)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=410,
        config=config,
        policy="replace",
    )

    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [7410],
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
        cohort_id=411,
        config=config,
        policy="replace",
    )

    definition = SubsetDefinition(
        subset_name="intersect-411",
        parent_cohort_id=410,
        operators=(
            CohortSubsetOperator(
                subset_cohort_id=411,
                relationship="intersect",
                window_start_offset=-1,
                window_end_offset=1,
            ),
        ),
    )

    _ = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=412,
        config=config,
        policy="replace",
    )
    skipped = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=412,
        config=config,
        policy="replace_if_changed",
    )
    assert skipped.status == "skipped"

    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "condition_occurrence_id": [7510, 7511],
                "condition_concept_id": [444, 444],
                "condition_start_date": ["2020-01-01", "2020-01-01"],
                "condition_end_date": ["2020-01-01", "2020-01-01"],
            }
        ),
        overwrite=True,
    )
    _ = generate_cohort(
        make_expression(444),
        backend=conn,
        cohort_id=411,
        config=config,
        policy="replace_if_changed",
    )

    regenerated = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=412,
        config=config,
        policy="replace_if_changed",
    )
    assert regenerated.status in {"generated", "replaced"}
