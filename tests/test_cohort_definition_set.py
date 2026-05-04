"""Tests for CohortDefinitionSet and generate_cohort_set."""

from __future__ import annotations

import pytest

from circe.cohort_definition_set import (
    CohortDefinition,
    CohortDefinitionSet,
    CohortGenerationResult,
    generate_cohort_set,
    summarise_generation_results,
)
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _simple_expression(concept_id: int = 111, set_id: int = 1) -> CohortExpression:
    return CohortExpression(
        concept_sets=[_make_concept_set(set_id, concept_id)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=set_id)]),
    )


def _seed_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "year_of_birth": [1980, 1982],
                "gender_concept_id": [8507, 8507],
            }
        ),
        overwrite=True,
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
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "condition_occurrence_id": [100, 101],
                "condition_concept_id": [111, 111],
                "condition_start_date": ["2020-01-01", "2020-01-02"],
                "condition_end_date": ["2020-01-01", "2020-01-02"],
            }
        ),
        overwrite=True,
    )


# ---------------------------------------------------------------------------
# CohortDefinitionSet — unit tests (no database needed)
# ---------------------------------------------------------------------------


def test_cohort_definition_set_add_and_iter():
    expr = _simple_expression()
    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="Cohort A", expression=expr)
    cds.add(cohort_id=2, cohort_name="Cohort B", expression=expr)

    assert len(cds) == 2
    ids = [c.cohort_id for c in cds]
    assert ids == [1, 2]


def test_cohort_definition_set_duplicate_id_raises():
    expr = _simple_expression()
    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="Cohort A", expression=expr)
    with pytest.raises(ValueError, match="cohort_id=1"):
        cds.add(cohort_id=1, cohort_name="Duplicate", expression=expr)


def test_cohort_definition_set_getitem():
    expr = _simple_expression()
    cds = CohortDefinitionSet()
    cds.add(cohort_id=42, cohort_name="My Cohort", expression=expr)

    item = cds[42]
    assert isinstance(item, CohortDefinition)
    assert item.cohort_id == 42
    assert item.cohort_name == "My Cohort"


def test_cohort_definition_set_getitem_missing_raises():
    cds = CohortDefinitionSet()
    with pytest.raises(KeyError):
        _ = cds[999]


def test_checksums_returns_dict():
    expr1 = _simple_expression(concept_id=111)
    expr2 = _simple_expression(concept_id=222, set_id=2)
    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="A", expression=expr1)
    cds.add(cohort_id=2, cohort_name="B", expression=expr2)

    checksums = cds.checksums()
    assert set(checksums.keys()) == {1, 2}
    assert isinstance(checksums[1], str)
    assert len(checksums[1]) == 64  # SHA-256 hex digest
    # Different expressions produce different checksums
    assert checksums[1] != checksums[2]


def test_checksums_stable():
    expr = _simple_expression()
    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="A", expression=expr)

    assert cds.checksums()[1] == cds.checksums()[1]


# ---------------------------------------------------------------------------
# generate_cohort_set — integration tests using DuckDB
# ---------------------------------------------------------------------------


def test_generate_cohort_set_basic():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    cds = CohortDefinitionSet()
    cds.add(cohort_id=10, cohort_name="Cohort 10", expression=_simple_expression())
    cds.add(cohort_id=20, cohort_name="Cohort 20", expression=_simple_expression())

    results = generate_cohort_set(cds, backend=conn, cdm_schema="main", cohort_table="cohort_out")

    assert len(results) == 2
    assert all(r.status == "COMPLETE" for r in results)
    assert {r.cohort_id for r in results} == {10, 20}

    cohort_table = conn.table("cohort_out").execute()
    assert len(cohort_table) == 4  # 2 persons × 2 cohorts
    assert set(cohort_table.cohort_definition_id) == {10, 20}


def test_generate_cohort_set_results_have_timing():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="A", expression=_simple_expression())

    results = generate_cohort_set(cds, backend=conn, cdm_schema="main", cohort_table="c")

    r = results[0]
    assert r.start_time <= r.end_time
    assert isinstance(r.checksum, str) and len(r.checksum) == 64


def test_generate_cohort_set_incremental_skip():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="A", expression=_simple_expression())
    cds.add(cohort_id=2, cohort_name="B", expression=_simple_expression())

    # First run: both should be COMPLETE
    first = generate_cohort_set(cds, backend=conn, cdm_schema="main", cohort_table="cohort", incremental=True)
    assert all(r.status == "COMPLETE" for r in first)

    # Second run with same expressions: both should be SKIPPED
    second = generate_cohort_set(
        cds, backend=conn, cdm_schema="main", cohort_table="cohort", incremental=True
    )
    assert all(r.status == "SKIPPED" for r in second)


def test_generate_cohort_set_incremental_regenerate():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    expr_a = _simple_expression(concept_id=111)
    expr_b = _simple_expression(concept_id=111)

    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="A", expression=expr_a)
    cds.add(cohort_id=2, cohort_name="B", expression=expr_b)

    generate_cohort_set(cds, backend=conn, cdm_schema="main", cohort_table="cohort", incremental=True)

    # Change cohort 1's expression (different concept)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [200],
                "condition_concept_id": [222],
                "condition_start_date": ["2020-03-01"],
                "condition_end_date": ["2020-03-01"],
            }
        ),
        overwrite=True,
    )
    expr_a_changed = _simple_expression(concept_id=222)  # different concept

    cds2 = CohortDefinitionSet()
    cds2.add(cohort_id=1, cohort_name="A", expression=expr_a_changed)
    cds2.add(cohort_id=2, cohort_name="B", expression=expr_b)  # unchanged

    results = generate_cohort_set(
        cds2, backend=conn, cdm_schema="main", cohort_table="cohort", incremental=True
    )

    statuses = {r.cohort_id: r.status for r in results}
    assert statuses[1] == "COMPLETE"  # regenerated
    assert statuses[2] == "SKIPPED"  # unchanged


def test_generate_cohort_set_incremental_non_incremental_does_not_skip():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="A", expression=_simple_expression())

    generate_cohort_set(cds, backend=conn, cdm_schema="main", cohort_table="cohort", incremental=True)

    # Non-incremental run should always be COMPLETE regardless of stored checksums
    results = generate_cohort_set(
        cds, backend=conn, cdm_schema="main", cohort_table="cohort", incremental=False
    )
    assert results[0].status == "COMPLETE"


def test_generate_cohort_set_continue_on_error():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    # Use a CohortExpression with a concept set referencing a missing table domain
    # by using a bad backend-level call; we monkeypatch write_cohort instead.
    from unittest.mock import patch

    from circe.execution.errors import ExecutionError

    call_count = 0

    def _failing_write_cohort(expression, *, cohort_id, **kwargs):
        nonlocal call_count
        call_count += 1
        if cohort_id == 1:
            raise ExecutionError("Simulated failure for cohort 1")
        # Delegate to real write_cohort for cohort 2
        from circe.execution.api import write_cohort as real_write_cohort

        real_write_cohort(expression, cohort_id=cohort_id, **kwargs)

    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="Bad", expression=_simple_expression())
    cds.add(cohort_id=2, cohort_name="Good", expression=_simple_expression())

    with patch("circe.cohort_definition_set._generate.write_cohort", side_effect=_failing_write_cohort):
        results = generate_cohort_set(
            cds,
            backend=conn,
            cdm_schema="main",
            cohort_table="cohort",
            stop_on_error=False,
        )

    assert call_count == 2
    statuses = {r.cohort_id: r.status for r in results}
    assert statuses[1] == "FAILED"
    assert statuses[2] == "COMPLETE"
    assert results[0].error is not None


def test_generate_cohort_set_stop_on_error():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    from unittest.mock import patch

    from circe.execution.errors import ExecutionError

    def _always_fail(expression, *, cohort_id, **kwargs):
        raise ExecutionError("Always fail")

    cds = CohortDefinitionSet()
    cds.add(cohort_id=1, cohort_name="Bad", expression=_simple_expression())
    cds.add(cohort_id=2, cohort_name="Also bad", expression=_simple_expression())

    with (
        patch("circe.cohort_definition_set._generate.write_cohort", side_effect=_always_fail),
        pytest.raises(ExecutionError, match="Always fail"),
    ):
        generate_cohort_set(
            cds,
            backend=conn,
            cdm_schema="main",
            cohort_table="cohort",
            stop_on_error=True,
        )


def test_summarise_generation_results():
    from datetime import datetime

    now = datetime.now()

    results = [
        CohortGenerationResult(1, "A", "COMPLETE", "abc", now, now),
        CohortGenerationResult(2, "B", "SKIPPED", "def", now, now),
        CohortGenerationResult(3, "C", "FAILED", "ghi", now, now),
        CohortGenerationResult(4, "D", "COMPLETE", "jkl", now, now),
    ]

    summary = summarise_generation_results(results)
    assert summary["COMPLETE"] == 2
    assert summary["SKIPPED"] == 1
    assert summary["FAILED"] == 1


def test_api_exports_cohort_definition_set():
    import circe.api as api

    assert hasattr(api, "CohortDefinitionSet")
    assert hasattr(api, "CohortDefinition")
    assert hasattr(api, "CohortGenerationResult")
    assert hasattr(api, "generate_cohort_set")
    assert hasattr(api, "summarise_generation_results")
