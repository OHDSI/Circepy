from __future__ import annotations

import pytest

from circe.api import build_cohort_ibis
from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    DemographicCriteria,
    Occurrence,
    PrimaryCriteria,
    Window,
    WindowBound,
)
from circe.execution.errors import UnsupportedFeatureError
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(
            items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
        ),
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


def test_additional_criteria_all_filters_primary_events():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 2],
                "condition_occurrence_id": [100, 101, 102],
                "condition_concept_id": [111, 222, 111],
                "condition_start_date": ["2020-01-01", "2020-01-02", "2020-01-01"],
                "condition_end_date": ["2020-01-01", "2020-01-02", "2020-01-01"],
                "visit_occurrence_id": [10, 10, 20],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=2),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                )
            ],
        ),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}


@pytest.mark.parametrize(
    ("group_type", "count", "expected_persons"),
    [
        ("ANY", None, {1, 2, 3}),
        ("ALL", None, {3}),
        ("AT_LEAST", 2, {3}),
        ("AT_MOST", 1, {1, 2}),
    ],
)
def test_additional_group_operators(group_type, count, expected_persons):
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
        additional_criteria=CriteriaGroup(
            type=group_type,
            count=count,
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=2),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                ),
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=3),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                ),
            ],
        ),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == expected_persons


def test_correlated_criteria_respects_restrict_visit_and_start_window():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 2, 2],
                "condition_occurrence_id": [100, 101, 200, 201],
                "condition_concept_id": [111, 222, 111, 222],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-06",
                    "2020-01-01",
                    "2020-01-10",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-06",
                    "2020-01-01",
                    "2020-01-10",
                ],
                "visit_occurrence_id": [10, 10, 20, 21],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=2),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                    restrict_visit=True,
                    start_window=Window(
                        start=WindowBound(coeff=1, days=0),
                        end=WindowBound(coeff=1, days=7),
                        use_event_end=False,
                        use_index_end=False,
                    ),
                )
            ],
        ),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    # Person 1 matches (same visit, +5 days). Person 2 fails (different visit and +9 days).
    assert set(result.person_id) == {1}


def test_additional_demographic_criteria_groups_raise_unsupported_feature():
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
        additional_criteria=CriteriaGroup(
            type="ALL",
            demographic_criteria_list=[
                DemographicCriteria(gender=[Concept(conceptId=8507)])
            ],
        ),
    )

    with pytest.raises(
        UnsupportedFeatureError,
        match="Demographic criteria groups are not implemented",
    ):
        _ = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
