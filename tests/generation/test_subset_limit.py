from __future__ import annotations

from datetime import date

from circe.api import generate_cohort, generate_subset
from circe.generation import GenerationConfig
from circe.generation.subsets.definitions import LimitSubsetOperator, SubsetDefinition

from tests.generation.conftest import make_expression, seed_base_tables


def test_limit_subset_first_only_and_calendar_filters(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=2)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=200,
        config=config,
        policy="replace",
    )

    cohort = conn.table("cohort", database="main").execute()
    appended = cohort.to_dict(orient="list")
    appended["cohort_start_date"] = [str(v) for v in appended["cohort_start_date"]]
    appended["cohort_end_date"] = [str(v) for v in appended["cohort_end_date"]]
    appended["cohort_definition_id"].append(200)
    appended["subject_id"].append(1)
    appended["cohort_start_date"].append("2020-06-01")
    appended["cohort_end_date"].append("2020-06-10")
    conn.create_table(
        "cohort",
        obj=ibis.memtable(appended),
        database="main",
        overwrite=True,
    )

    definition = SubsetDefinition(
        subset_name="first-rows",
        parent_cohort_id=200,
        operators=(
            LimitSubsetOperator(
                first_only=True,
                min_prior_observation_days=30,
                min_cohort_duration_days=0,
                calendar_start_date=date(2020, 1, 1),
                calendar_end_date=date(2020, 12, 31),
            ),
        ),
    )

    status = generate_subset(
        definition,
        backend=conn,
        generated_cohort_id=201,
        config=config,
        policy="replace",
    )

    assert status.status in {"generated", "replaced"}
    result = conn.table("cohort", database="main").filter(
        conn.table("cohort", database="main").cohort_definition_id == 201
    ).execute()
    assert set(result.subject_id) == {1, 2}
    assert len(result) == 2
