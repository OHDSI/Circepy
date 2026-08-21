from __future__ import annotations

import pytest

from circe.api import build_cohort
from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    InclusionRule,
    Occurrence,
    PrimaryCriteria,
)
from circe.execution.api import build_cohort as build_execution_cohort
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _seed_common_tables(conn, ibis, *, persons=(1, 2, 3)):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": list(persons),
                "year_of_birth": [1980 for _ in persons],
                "gender_concept_id": [8507 for _ in persons],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": list(persons),
                "observation_period_id": [10 + idx for idx, _ in enumerate(persons)],
                "observation_period_start_date": ["2019-01-01" for _ in persons],
                "observation_period_end_date": ["2022-12-31" for _ in persons],
            }
        ),
        overwrite=True,
    )


def test_inclusion_rules_require_all_rules_to_match():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2, 3))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 2, 2, 3, 3, 3],
                "condition_occurrence_id": [100, 101, 200, 201, 300, 301, 302],
                "condition_concept_id": [111, 222, 111, 333, 111, 222, 333],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                ],
                "visit_occurrence_id": [10, 10, 20, 20, 30, 30, 30],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 222),
            _make_concept_set(3, 333),
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        inclusion_rules=[
            InclusionRule(
                name="rule-1",
                expression=CriteriaGroup(
                    type="ALL",
                    criteria_list=[
                        CorelatedCriteria(
                            criteria=ConditionOccurrence(codeset_id=2),
                            occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                        )
                    ],
                ),
            ),
            InclusionRule(
                name="rule-2",
                expression=CriteriaGroup(
                    type="ALL",
                    criteria_list=[
                        CorelatedCriteria(
                            criteria=ConditionOccurrence(codeset_id=3),
                            occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                        )
                    ],
                ),
            ),
        ],
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {3}


def test_inclusion_rule_without_expression_is_noop():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "condition_occurrence_id": [100, 200],
                "condition_concept_id": [111, 111],
                "condition_start_date": ["2020-01-01", "2020-01-01"],
                "condition_end_date": ["2020-01-01", "2020-01-01"],
                "visit_occurrence_id": [10, 20],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        inclusion_rules=[InclusionRule(name="empty", expression=None)],
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1, 2}


def test_inclusion_rules_materialize_false_matches_materialized_result():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2, 3, 4))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 2, 2, 3, 3, 3, 4, 4],
                "condition_occurrence_id": [100, 101, 102, 200, 201, 300, 301, 302, 400, 401],
                "condition_concept_id": [111, 222, 333, 111, 222, 111, 222, 333, 111, 333],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-01",
                    "2020-01-02",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-01",
                    "2020-01-02",
                ],
                "visit_occurrence_id": [10, 10, 10, 20, 20, 30, 30, 30, 40, 40],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 222),
            _make_concept_set(3, 333),
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        inclusion_rules=[
            InclusionRule(
                name="rule-1",
                expression=CriteriaGroup(
                    type="ALL",
                    criteria_list=[
                        CorelatedCriteria(
                            criteria=ConditionOccurrence(codeset_id=2),
                            occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                        )
                    ],
                ),
            ),
            InclusionRule(
                name="rule-2",
                expression=CriteriaGroup(
                    type="ALL",
                    criteria_list=[
                        CorelatedCriteria(
                            criteria=ConditionOccurrence(codeset_id=3),
                            occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                        )
                    ],
                ),
            ),
            InclusionRule(name="noop", expression=None),
        ],
    )

    materialized = build_execution_cohort(
        expression,
        backend=conn,
        cdm_schema="main",
        materialize=True,
    ).execute()
    non_materialized = build_execution_cohort(
        expression,
        backend=conn,
        cdm_schema="main",
        materialize=False,
    ).execute()

    materialized_rows = {
        tuple(row)
        for row in materialized[["person_id", "event_id", "start_date", "end_date"]].itertuples(
            index=False, name=None
        )
    }
    non_materialized_rows = {
        tuple(row)
        for row in non_materialized[["person_id", "event_id", "start_date", "end_date"]].itertuples(
            index=False, name=None
        )
    }

    assert non_materialized_rows == materialized_rows
    assert materialized_rows
