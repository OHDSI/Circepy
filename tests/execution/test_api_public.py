from __future__ import annotations

import pytest

import circe.api as api
from circe.api import (
    build_cohort,
    build_cohort_ibis,
    write_cohort,
    write_cohort_ibis,
)
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.execution.api import write_relation
from circe.execution.errors import ExecutionError
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(
            items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
        ),
    )


def _expression() -> CohortExpression:
    return CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
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


def test_public_aliases_resolve_to_canonical_functions():
    assert hasattr(api, "build_cohort")
    assert hasattr(api, "write_cohort")
    assert hasattr(api, "build_cohort_query")
    assert hasattr(api, "build_cohort_ibis")
    assert hasattr(api, "write_cohort_ibis")
    assert build_cohort_ibis is build_cohort
    assert write_cohort_ibis is write_cohort


def test_build_cohort_returns_relation_and_alias_works():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    expression = _expression()

    relation = build_cohort(expression, backend=conn, cdm_schema="main")
    alias_relation = build_cohort_ibis(expression, backend=conn, cdm_schema="main")

    assert hasattr(relation, "execute")
    assert len(relation.execute()) == len(alias_relation.execute())


def test_write_cohort_writes_result_table():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    write_cohort(
        _expression(),
        backend=conn,
        cdm_schema="main",
        target_table="cohort_out",
        if_exists="replace",
    )
    result = conn.table("cohort_out").execute()
    assert len(result) == 2


def test_write_cohort_if_exists_fail_raises():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    write_cohort(
        _expression(),
        backend=conn,
        cdm_schema="main",
        target_table="cohort_out",
        if_exists="fail",
    )
    with pytest.raises(ExecutionError, match="failed writing relation"):
        write_cohort(
            _expression(),
            backend=conn,
            cdm_schema="main",
            target_table="cohort_out",
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
        target_table="cohort_out",
        if_exists="replace",
    )
    first = conn.table("cohort_out").execute()
    assert len(first) == 2

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
        target_table="cohort_out",
        if_exists="replace",
    )
    replaced = conn.table("cohort_out").execute()
    assert set(replaced.person_id) == {1}


def test_write_cohort_respects_results_schema_and_temporary():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    write_cohort(
        _expression(),
        backend=conn,
        cdm_schema="main",
        results_schema="main",
        target_table="cohort_schema",
        if_exists="replace",
    )
    assert len(conn.table("cohort_schema", database="main").execute()) == 2

    write_cohort_ibis(
        _expression(),
        backend=conn,
        cdm_schema="main",
        target_table="cohort_temp",
        if_exists="replace",
        temporary=True,
    )
    assert len(conn.table("cohort_temp").execute()) == 2


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
        results_schema="main",
        if_exists="replace",
    )
    result = conn.table("cohort_filtered", database="main").execute()
    assert set(result.person_id) == {1}
