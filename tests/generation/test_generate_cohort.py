from __future__ import annotations

import pytest

from circe.api import generate_cohort, get_generated_cohort_status
from circe.generation import GenerationConfig

from tests.generation.conftest import make_expression, seed_base_tables


def test_generate_cohort_new_writes_rows_and_metadata(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=2)

    config = GenerationConfig(cdm_schema="main", results_schema="main")

    status = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=1,
        cohort_name="C1",
        config=config,
        policy="replace",
    )

    assert status.status in {"generated", "replaced"}
    cohort = conn.table(config.cohort_table, database="main").execute()
    assert set(cohort.columns) == {
        "cohort_definition_id",
        "subject_id",
        "cohort_start_date",
        "cohort_end_date",
    }
    assert set(cohort.cohort_definition_id) == {1}
    assert len(cohort) == 2

    metadata = conn.table(config.metadata_table, database="main").execute()
    checksums = conn.table(config.checksum_table, database="main").execute()
    assert set(metadata.cohort_id) == {1}
    assert set(checksums.cohort_id) == {1}

    inspected = get_generated_cohort_status(backend=conn, cohort_id=1, config=config)
    assert inspected.status in {"generated", "replaced", "skipped"}
    assert inspected.combined_hash is not None


def test_generate_cohort_policy_fail_blocks_existing(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=1)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=10,
        config=config,
        policy="replace",
    )

    with pytest.raises(RuntimeError, match="policy 'fail' blocked"):
        _ = generate_cohort(
            make_expression(111),
            backend=conn,
            cohort_id=10,
            config=config,
            policy="fail",
        )


def test_generate_cohort_policy_skip_if_same(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=1)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=20,
        config=config,
        policy="replace",
    )
    second = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=20,
        config=config,
        policy="skip_if_same",
    )

    assert second.status == "skipped"


def test_generate_cohort_policy_replace_if_changed(ibis_duckdb_conn):
    ibis, conn = ibis_duckdb_conn
    seed_base_tables(ibis, conn, concept_id=111, rows=1)

    config = GenerationConfig(cdm_schema="main", results_schema="main")
    _ = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=30,
        config=config,
        policy="replace",
    )

    unchanged = generate_cohort(
        make_expression(111),
        backend=conn,
        cohort_id=30,
        config=config,
        policy="replace_if_changed",
    )
    assert unchanged.status == "skipped"

    seed_base_tables(ibis, conn, concept_id=222, rows=1)
    changed = generate_cohort(
        make_expression(222),
        backend=conn,
        cohort_id=30,
        config=config,
        policy="replace_if_changed",
    )
    assert changed.status in {"generated", "replaced"}

    cohort = conn.table(config.cohort_table, database="main").execute()
    assert set(cohort.cohort_definition_id) == {30}
    assert len(cohort) == 1
