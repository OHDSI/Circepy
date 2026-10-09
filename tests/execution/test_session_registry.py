"""Tests for the session-activity registry (stale staging-table detection)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from circe.api import build_cohort, write_cohort
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.execution.session import (
    SESSION_TABLE,
    StaleSession,
    cleanup_stale_sessions,
    list_stale_sessions,
    register_session,
    report_stale_sessions,
    unregister_session,
)
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _cohort_expression(concept_id: int = 111) -> CohortExpression:
    return CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
                ),
            )
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )


def _seed_cdm(conn, ibis, schema: str | None = None) -> None:
    kw = {"database": schema} if schema is not None else {}
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {"person_id": [1, 2], "year_of_birth": [1980, 1980], "gender_concept_id": [8507, 8507]}
        ),
        overwrite=True,
        **kw,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "observation_period_id": [10, 11],
                "observation_period_start_date": ["2019-01-01", "2019-01-01"],
                "observation_period_end_date": ["2021-12-31", "2021-12-31"],
            }
        ),
        overwrite=True,
        **kw,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "condition_occurrence_id": [100, 101],
                "condition_concept_id": [111, 999],
                "condition_start_date": ["2020-01-01", "2020-01-01"],
                "condition_end_date": ["2020-01-01", "2020-01-01"],
            }
        ),
        overwrite=True,
        **kw,
    )


def _seed_staging_tables(conn, ibis, prefix: str) -> None:
    conn.create_table(
        f"{prefix}__codesets", obj=ibis.memtable({"codeset_id": [1], "concept_id": [1]}), overwrite=True
    )
    conn.create_table(
        f"{prefix}__staging_ended",
        obj=ibis.memtable({"person_id": [1]}),
        overwrite=True,
    )


def test_register_and_unregister_round_trip():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    register_session(conn, schema="main", session_prefix="__c_abc_")

    registry = conn.table(SESSION_TABLE, database="main").execute()
    assert list(registry["session_prefix"]) == ["__c_abc_"]

    unregister_session(conn, schema="main", session_prefix="__c_abc_")
    assert conn.table(SESSION_TABLE, database="main").count().execute() == 0


def test_register_is_idempotent_upsert():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    register_session(conn, schema="main", session_prefix="__c_abc_", now=datetime(2026, 1, 1))
    register_session(conn, schema="main", session_prefix="__c_abc_", now=datetime(2026, 2, 1))

    registry = conn.table(SESSION_TABLE, database="main").execute()
    assert len(registry) == 1
    assert list(registry["session_prefix"]) == ["__c_abc_"]


def test_list_stale_sessions_detects_orphans_and_prunes_missing():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    # Old session whose staging tables still exist -> reported as stale.
    register_session(conn, schema="main", session_prefix="__c_old_", now=datetime(2026, 1, 1))
    _seed_staging_tables(conn, ibis, "__c_old_")

    # Fresh session -> not reported.
    register_session(conn, schema="main", session_prefix="__c_new_", now=datetime.now())
    _seed_staging_tables(conn, ibis, "__c_new_")

    # Old session whose tables were already dropped -> pruned, not reported.
    register_session(conn, schema="main", session_prefix="__c_gone_", now=datetime(2026, 1, 1))

    stale = list_stale_sessions(conn, schema="main", older_than=timedelta(days=7))

    assert [s.session_prefix for s in stale] == ["__c_old_"]
    assert isinstance(stale[0], StaleSession)
    assert set(stale[0].tables) == {"__c_old___codesets", "__c_old___staging_ended"}

    # The pruned registration is gone from the registry.
    remaining = conn.table(SESSION_TABLE, database="main").execute()
    assert set(remaining["session_prefix"]) == {"__c_old_", "__c_new_"}


def test_list_stale_sessions_empty_without_registry():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    assert list_stale_sessions(conn, schema="main") == []


def test_report_stale_sessions_logs_warning(caplog):
    import logging

    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    register_session(conn, schema="main", session_prefix="__c_old_", now=datetime(2026, 1, 1))
    _seed_staging_tables(conn, ibis, "__c_old_")

    with caplog.at_level(logging.WARNING, logger="circe.execution.session"):
        stale = report_stale_sessions(conn, schema="main", older_than=timedelta(days=7))

    assert len(stale) == 1
    assert any("stale Circe staging table group(s)" in r.message for r in caplog.records)


def test_cleanup_stale_sessions_drops_tables_and_unregisters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    register_session(conn, schema="main", session_prefix="__c_old_", now=datetime(2026, 1, 1))
    _seed_staging_tables(conn, ibis, "__c_old_")

    dropped = cleanup_stale_sessions(conn, schema="main", older_than=timedelta(days=7))

    assert set(dropped) == {"__c_old___codesets", "__c_old___staging_ended"}
    assert "__c_old___staging_ended" not in conn.list_tables()
    assert conn.table(SESSION_TABLE, database="main").count().execute() == 0


def test_write_cohort_unregisters_and_build_cohort_registers():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_cdm(conn, ibis)

    write_cohort(_cohort_expression(), backend=conn, cdm_schema="main", cohort_table="cohort", cohort_id=1)
    assert conn.table(SESSION_TABLE, database="main").count().execute() == 0

    build_cohort(_cohort_expression(), backend=conn, cdm_schema="main")
    registry = conn.table(SESSION_TABLE, database="main").execute()
    assert len(registry) == 1
    assert str(registry.iloc[0]["session_prefix"]).startswith("__c_")


def test_write_cohort_leaves_no_staging_or_codeset_in_any_schema():
    """codeset + staging share cdm_schema when results_schema is None (#57)."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    conn.raw_sql("CREATE SCHEMA cdm")
    _seed_cdm(conn, ibis, schema="cdm")

    write_cohort(_cohort_expression(), backend=conn, cdm_schema="cdm", cohort_table="cohort", cohort_id=1)

    assert [t for t in conn.list_tables() if t.startswith("__")] == []
    assert [t for t in conn.list_tables(database="cdm") if t.startswith("__")] == []
    assert conn.table(SESSION_TABLE, database="cdm").count().execute() == 0
