from __future__ import annotations

import pytest

import circe.api as api
from circe.api import build_cohort, write_cohort
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.execution.api import write_relation
from circe.execution.errors import ExecutionError
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _expression() -> CohortExpression:
    return CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
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


def test_public_execution_functions_are_exported():
    assert hasattr(api, "build_cohort")
    assert hasattr(api, "write_cohort")
    assert hasattr(api, "build_cohort_query")


def test_build_cohort_returns_relation():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    expression = _expression()

    relation = build_cohort(expression, backend=conn, cdm_schema="main")

    assert hasattr(relation, "execute")
    assert len(relation.execute()) == 2


def test_write_cohort_writes_result_table():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    write_cohort(
        _expression(),
        backend=conn,
        cdm_schema="main",
        cohort_table="cohort_out",
        cohort_id=42,
        if_exists="replace",
    )
    result = conn.table("cohort_out").execute()
    assert len(result) == 2
    assert list(result.columns) == [
        "cohort_definition_id",
        "subject_id",
        "cohort_start_date",
        "cohort_end_date",
    ]
    assert set(result.cohort_definition_id) == {42}


def test_write_cohort_if_exists_fail_raises():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    write_cohort(
        _expression(),
        backend=conn,
        cdm_schema="main",
        cohort_table="cohort_out",
        cohort_id=42,
        if_exists="fail",
    )
    with pytest.raises(ExecutionError, match="already contains rows for cohort_id=42"):
        write_cohort(
            _expression(),
            backend=conn,
            cdm_schema="main",
            cohort_table="cohort_out",
            cohort_id=42,
            if_exists="fail",
        )


def test_write_cohort_if_exists_replace_overwrites():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)
    expression = _expression()

    write_cohort(
        expression,
        backend=conn,
        cdm_schema="main",
        cohort_table="cohort_out",
        cohort_id=10,
        if_exists="replace",
    )
    first = conn.table("cohort_out").execute()
    assert len(first) == 2
    assert set(first.cohort_definition_id) == {10}

    write_cohort(
        expression,
        backend=conn,
        cdm_schema="main",
        cohort_table="cohort_out",
        cohort_id=20,
        if_exists="replace",
    )
    combined = conn.table("cohort_out").execute()
    assert len(combined) == 4
    assert set(combined.cohort_definition_id) == {10, 20}

    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [100],
                "condition_concept_id": [111],
                "condition_start_date": ["2020-01-01"],
                "condition_end_date": ["2020-01-01"],
            }
        ),
        overwrite=True,
    )
    write_cohort(
        expression,
        backend=conn,
        cdm_schema="main",
        cohort_table="cohort_out",
        cohort_id=10,
        if_exists="replace",
    )
    replaced = conn.table("cohort_out").execute()
    replaced_10 = replaced[replaced.cohort_definition_id == 10]
    replaced_20 = replaced[replaced.cohort_definition_id == 20]
    assert set(replaced_10.subject_id) == {1}
    assert set(replaced_20.subject_id) == {1, 2}


def test_write_cohort_respects_results_schema():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    write_cohort(
        _expression(),
        backend=conn,
        cdm_schema="main",
        results_schema="main",
        cohort_table="cohort_schema",
        cohort_id=7,
        if_exists="replace",
    )
    assert len(conn.table("cohort_schema", database="main").execute()) == 2


def test_expression_first_build_modify_then_write_relation():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    relation = build_cohort(_expression(), backend=conn, cdm_schema="main")
    modified = relation.filter(relation.person_id == 1)

    write_relation(
        modified,
        backend=conn,
        target_table="cohort_filtered",
        target_schema="main",
        if_exists="replace",
    )
    result = conn.table("cohort_filtered", database="main").execute()
    assert set(result.person_id) == {1}


def test_write_cohort_rejects_invalid_if_exists():
    with pytest.raises(ValueError, match="if_exists must be one of"):
        write_cohort(
            _expression(),
            backend=object(),
            cdm_schema="main",
            cohort_table="cohort_out",
            cohort_id=1,
            if_exists="append",
        )


def test_write_cohort_replace_uses_delete_then_insert(monkeypatch: pytest.MonkeyPatch):
    import circe.execution.api as execution_api

    events: list[tuple[str, object]] = []

    monkeypatch.setattr(execution_api, "build_cohort", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        execution_api, "project_to_ohdsi_cohort_table", lambda relation, *, cohort_id: relation
    )
    monkeypatch.setattr(execution_api, "table_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr(execution_api, "supports_transactional_replace", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        execution_api,
        "replace_cohort_rows_transactionally",
        lambda relation, *, backend, cohort_table, results_schema=None, cohort_id: events.append(
            ("replace", cohort_table, results_schema, cohort_id)
        ),
    )
    monkeypatch.setattr(
        execution_api,
        "write_relation",
        lambda *args, **kwargs: events.append(("create", kwargs["target_table"])),
    )

    write_cohort(
        _expression(),
        backend=object(),
        cdm_schema="main",
        results_schema="results",
        cohort_table="cohort_out",
        cohort_id=9,
        if_exists="replace",
    )

    assert events == [("replace", "cohort_out", "results", 9)]


def test_write_cohort_replace_falls_back_to_safe_rewrite(monkeypatch: pytest.MonkeyPatch):
    import circe.execution.api as execution_api

    events: list[tuple[str, object]] = []
    existing = object()

    class _Filtered:
        def union(self, relation, distinct=False):
            events.append(("union", distinct))
            return "merged"

    filtered = _Filtered()

    monkeypatch.setattr(execution_api, "build_cohort", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        execution_api, "project_to_ohdsi_cohort_table", lambda relation, *, cohort_id: relation
    )
    monkeypatch.setattr(execution_api, "table_exists", lambda *args, **kwargs: True)
    monkeypatch.setattr(execution_api, "supports_transactional_replace", lambda *args, **kwargs: False)
    monkeypatch.setattr(execution_api, "read_table", lambda *args, **kwargs: existing)
    monkeypatch.setattr(
        execution_api,
        "exclude_cohort_rows",
        lambda relation, *, cohort_id: events.append(("filter", cohort_id)) or filtered,
    )
    monkeypatch.setattr(
        execution_api,
        "write_relation",
        lambda relation, *, backend, target_table, target_schema=None, if_exists="fail", temporary=False: (
            events.append(("write", relation, target_table, target_schema, if_exists))
        ),
    )

    write_cohort(
        _expression(),
        backend=object(),
        cdm_schema="main",
        results_schema="results",
        cohort_table="cohort_out",
        cohort_id=9,
        if_exists="replace",
    )

    assert events == [
        ("filter", 9),
        ("union", False),
        ("write", "merged", "cohort_out", "results", "replace"),
    ]


def test_write_relation_type_error_is_reported_as_generic_write_failure():
    class _Backend:
        def create_table(self, name, **kwargs):
            raise TypeError("boom")

    with pytest.raises(ExecutionError, match="failed writing relation to table 'cohort_out'"):
        write_relation(
            object(),
            backend=_Backend(),
            target_table="cohort_out",
            target_schema="main",
            if_exists="replace",
        )
