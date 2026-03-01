from __future__ import annotations

from circe.api import create_generation_tables, get_generated_cohort_status
from circe.generation import GenerationConfig


def test_create_generation_tables_and_missing_status(ibis_duckdb_conn):
    _, conn = ibis_duckdb_conn
    config = GenerationConfig(cdm_schema="main", results_schema="main")

    create_generation_tables(backend=conn, config=config)

    assert conn.table(config.metadata_table, database="main") is not None
    assert conn.table(config.checksum_table, database="main") is not None
    assert conn.table(config.subset_metadata_table, database="main") is not None

    status = get_generated_cohort_status(
        backend=conn,
        cohort_id=123,
        config=config,
    )
    assert status.status == "missing"
    assert status.cohort_id == 123
