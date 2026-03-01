from __future__ import annotations

from circe.api import apply_subset, generate_cohort, generate_subset
from circe.generation import GenerationConfig
from circe.generation.subsets.definitions import (
    DemographicSubsetOperator,
    SubsetDefinition,
)

from tests.generation.conftest import make_expression, seed_base_tables


def test_demographic_subset_apply_and_generate(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=3)

    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "year_of_birth": [1980, 2005, 1990],
                "gender_concept_id": [8507, 8532, 8507],
                "race_concept_id": [8527, 8527, 8516],
                "ethnicity_concept_id": [38003563, 38003563, 38003564],
            }
        ),
        overwrite=True,
    )

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=100,
        cohort_name="parent",
        config=config,
        policy="replace",
    )

    definition = SubsetDefinition(
        subset_name="adult-male",
        parent_cohort_id=100,
        operators=(
            DemographicSubsetOperator(
                age_range=(30, None),
                gender_concept_ids=(8507,),
                race_concept_ids=(8527,),
            ),
        ),
    )

    parent_relation = conn.table("cohort", database="main").filter(
        conn.table("cohort", database="main").cohort_definition_id == 100
    )
    transformed = apply_subset(
        parent_relation,
        backend=conn,
        config=config,
        definition=definition,
    )
    transformed_rows = transformed.execute()
    assert set(transformed_rows.subject_id) == {1}

    status = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=101,
        config=config,
        policy="replace",
    )
    assert status.status in {"generated", "replaced"}

    cohort = conn.table("cohort", database="main").execute()
    subset_rows = cohort[cohort["cohort_definition_id"] == 101]
    assert set(subset_rows["subject_id"]) == {1}
