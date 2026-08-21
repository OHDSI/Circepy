from __future__ import annotations

import pytest

from circe.api import build_cohort
from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaColumn,
    CriteriaGroup,
    DemographicCriteria,
    DrugEra,
    Occurrence,
    PrimaryCriteria,
    Window,
    WindowBound,
)
from circe.cohortdefinition.core import DateRange, NumericRange
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

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
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

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
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

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    # Person 1 matches (same visit, +5 days). Person 2 fails (different visit and +9 days).
    assert set(result.person_id) == {1}


def test_additional_demographic_criteria_groups_filter_primary_events():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2, 3))
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "year_of_birth": [1980, 1980, 2010],
                "gender_concept_id": [8507, 8507, 8507],
                "race_concept_id": [8527, 8516, 8527],
                "ethnicity_concept_id": [38003564, 38003564, 38003563],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "condition_occurrence_id": [100, 200, 300],
                "condition_concept_id": [111, 111, 111],
                "condition_start_date": ["2020-01-03", "2020-01-03", "2020-01-03"],
                "condition_end_date": ["2020-01-03", "2020-01-03", "2020-01-03"],
                "visit_occurrence_id": [10, 20, 30],
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
                DemographicCriteria(
                    age=NumericRange(op="gte", value=18),
                    gender=[Concept(conceptId=8507)],
                    race=[Concept(conceptId=8527)],
                    ethnicity=[Concept(conceptId=38003564)],
                    occurrence_start_date=DateRange(op="gte", value="2020-01-02"),
                )
            ],
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}


def test_nested_correlated_criteria_inside_group_are_applied():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 2, 2],
                "condition_occurrence_id": [100, 101, 102, 200, 201],
                "condition_concept_id": [111, 222, 333, 111, 222],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-15",
                    "2020-01-01",
                    "2020-01-10",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-15",
                    "2020-01-01",
                    "2020-01-10",
                ],
                "visit_occurrence_id": [10, 10, 10, 20, 20],
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
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(
                        codeset_id=2,
                        correlated_criteria=CriteriaGroup(
                            type="ALL",
                            criteria_list=[
                                CorelatedCriteria(
                                    criteria=ConditionOccurrence(codeset_id=3),
                                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                                    start_window=Window(
                                        start=WindowBound(coeff=1, days=0),
                                        end=WindowBound(coeff=1, days=10),
                                        use_event_end=False,
                                        use_index_end=False,
                                    ),
                                )
                            ],
                        ),
                    ),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                    start_window=Window(
                        start=WindowBound(coeff=1, days=0),
                        end=WindowBound(coeff=1, days=20),
                        use_event_end=False,
                        use_index_end=False,
                    ),
                )
            ],
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}


def test_nested_correlated_inner_any_mode_with_multiple_children():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2, 3))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 2, 2, 3, 3],
                "condition_occurrence_id": [100, 101, 102, 200, 201, 300, 301],
                "condition_concept_id": [111, 222, 333, 111, 222, 111, 444],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-12",
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-01",
                    "2020-01-12",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-12",
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-01",
                    "2020-01-12",
                ],
                "visit_occurrence_id": [10, 10, 10, 20, 20, 30, 30],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 222),
            _make_concept_set(3, 333),
            _make_concept_set(4, 444),
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(
                        codeset_id=2,
                        correlated_criteria=CriteriaGroup(
                            type="ANY",
                            criteria_list=[
                                CorelatedCriteria(
                                    criteria=ConditionOccurrence(codeset_id=3),
                                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                                    start_window=Window(
                                        start=WindowBound(coeff=1, days=0),
                                        end=WindowBound(coeff=1, days=5),
                                        use_event_end=False,
                                        use_index_end=False,
                                    ),
                                ),
                                CorelatedCriteria(
                                    criteria=ConditionOccurrence(codeset_id=4),
                                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                                    start_window=Window(
                                        start=WindowBound(coeff=1, days=0),
                                        end=WindowBound(coeff=1, days=5),
                                        use_event_end=False,
                                        use_index_end=False,
                                    ),
                                ),
                            ],
                        ),
                    ),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                    start_window=Window(
                        start=WindowBound(coeff=1, days=0),
                        end=WindowBound(coeff=1, days=20),
                        use_event_end=False,
                        use_index_end=False,
                    ),
                )
            ],
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}


def test_nested_correlated_group_demographics_are_applied():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "year_of_birth": [1980, 1980],
                "gender_concept_id": [8507, 8507],
                "race_concept_id": [8527, 8516],
                "ethnicity_concept_id": [38003564, 38003564],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 2, 2],
                "condition_occurrence_id": [100, 101, 200, 201],
                "condition_concept_id": [111, 222, 111, 222],
                "condition_start_date": ["2020-01-01", "2020-01-10", "2020-01-01", "2020-01-10"],
                "condition_end_date": ["2020-01-01", "2020-01-10", "2020-01-01", "2020-01-10"],
                "visit_occurrence_id": [10, 10, 20, 20],
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
                    criteria=ConditionOccurrence(
                        codeset_id=2,
                        correlated_criteria=CriteriaGroup(
                            type="ALL",
                            demographic_criteria_list=[
                                DemographicCriteria(
                                    age=NumericRange(op="gte", value=18),
                                    race=[Concept(conceptId=8527)],
                                )
                            ],
                        ),
                    ),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                    start_window=Window(
                        start=WindowBound(coeff=1, days=0),
                        end=WindowBound(coeff=1, days=20),
                        use_event_end=False,
                        use_index_end=False,
                    ),
                )
            ],
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}


def test_nested_correlated_distinct_count_is_applied():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 1, 2, 2, 2, 2],
                "condition_occurrence_id": [100, 101, 102, 103, 200, 201, 202, 203],
                "condition_concept_id": [111, 222, 333, 333, 111, 222, 333, 333],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-11",
                    "2020-01-12",
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-11",
                    "2020-01-11",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-11",
                    "2020-01-12",
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-11",
                    "2020-01-11",
                ],
                "visit_occurrence_id": [10, 10, 10, 10, 20, 20, 20, 20],
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
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(
                        codeset_id=2,
                        correlated_criteria=CriteriaGroup(
                            type="ALL",
                            criteria_list=[
                                CorelatedCriteria(
                                    criteria=ConditionOccurrence(codeset_id=3),
                                    occurrence=Occurrence(
                                        type=Occurrence._AT_LEAST,
                                        count=2,
                                        is_distinct=True,
                                        count_column=CriteriaColumn.START_DATE,
                                    ),
                                    start_window=Window(
                                        start=WindowBound(coeff=1, days=0),
                                        end=WindowBound(coeff=1, days=5),
                                        use_event_end=False,
                                        use_index_end=False,
                                    ),
                                )
                            ],
                        ),
                    ),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                    start_window=Window(
                        start=WindowBound(coeff=1, days=0),
                        end=WindowBound(coeff=1, days=20),
                        use_event_end=False,
                        use_index_end=False,
                    ),
                )
            ],
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}


def test_nested_correlated_end_window_respects_index_end():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 2, 2, 2],
                "condition_occurrence_id": [100, 101, 102, 200, 201, 202],
                "condition_concept_id": [111, 222, 333, 111, 222, 333],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-23",
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-27",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-20",
                    "2020-01-25",
                    "2020-01-01",
                    "2020-01-20",
                    "2020-01-29",
                ],
                "visit_occurrence_id": [10, 10, 10, 20, 20, 20],
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
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(
                        codeset_id=2,
                        correlated_criteria=CriteriaGroup(
                            type="ALL",
                            criteria_list=[
                                CorelatedCriteria(
                                    criteria=ConditionOccurrence(codeset_id=3),
                                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                                    end_window=Window(
                                        start=WindowBound(coeff=1, days=0),
                                        end=WindowBound(coeff=1, days=5),
                                        use_event_end=False,
                                        use_index_end=True,
                                    ),
                                )
                            ],
                        ),
                    ),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                    start_window=Window(
                        start=WindowBound(coeff=1, days=0),
                        end=WindowBound(coeff=1, days=20),
                        use_event_end=False,
                        use_index_end=False,
                    ),
                )
            ],
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}


def test_nested_correlated_ignore_observation_period_changes_matching():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1,))
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "observation_period_id": [10],
                "observation_period_start_date": ["2019-01-01"],
                "observation_period_end_date": ["2020-01-15"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1],
                "condition_occurrence_id": [100, 101, 102],
                "condition_concept_id": [111, 222, 333],
                "condition_start_date": ["2020-01-01", "2020-01-10", "2020-01-20"],
                "condition_end_date": ["2020-01-01", "2020-01-10", "2020-01-20"],
                "visit_occurrence_id": [10, 10, 10],
            }
        ),
        overwrite=True,
    )

    def _expression(ignore_observation_period: bool) -> CohortExpression:
        return CohortExpression(
            concept_sets=[
                _make_concept_set(1, 111),
                _make_concept_set(2, 222),
                _make_concept_set(3, 333),
            ],
            primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
            additional_criteria=CriteriaGroup(
                type="ALL",
                criteria_list=[
                    CorelatedCriteria(
                        criteria=ConditionOccurrence(
                            codeset_id=2,
                            correlated_criteria=CriteriaGroup(
                                type="ALL",
                                criteria_list=[
                                    CorelatedCriteria(
                                        criteria=ConditionOccurrence(codeset_id=3),
                                        occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                                        start_window=Window(
                                            start=WindowBound(coeff=1, days=0),
                                            end=WindowBound(coeff=1, days=15),
                                            use_event_end=False,
                                            use_index_end=False,
                                        ),
                                        ignore_observation_period=ignore_observation_period,
                                    )
                                ],
                            ),
                        ),
                        occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                        start_window=Window(
                            start=WindowBound(coeff=1, days=0),
                            end=WindowBound(coeff=1, days=20),
                            use_event_end=False,
                            use_index_end=False,
                        ),
                    )
                ],
            ),
        )

    without_ignore = build_cohort(_expression(False), backend=conn, cdm_schema="main").execute()
    with_ignore = build_cohort(_expression(True), backend=conn, cdm_schema="main").execute()

    assert len(without_ignore) == 0
    assert set(with_ignore.person_id) == {1}


def test_nested_correlated_multi_level_nesting_is_applied():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 1, 2, 2, 2],
                "condition_occurrence_id": [100, 101, 102, 103, 200, 201, 202],
                "condition_concept_id": [111, 222, 333, 444, 111, 222, 333],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-12",
                    "2020-01-14",
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-12",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-12",
                    "2020-01-14",
                    "2020-01-01",
                    "2020-01-10",
                    "2020-01-12",
                ],
                "visit_occurrence_id": [10, 10, 10, 10, 20, 20, 20],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _make_concept_set(1, 111),
            _make_concept_set(2, 222),
            _make_concept_set(3, 333),
            _make_concept_set(4, 444),
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(
                        codeset_id=2,
                        correlated_criteria=CriteriaGroup(
                            type="ALL",
                            criteria_list=[
                                CorelatedCriteria(
                                    criteria=ConditionOccurrence(
                                        codeset_id=3,
                                        correlated_criteria=CriteriaGroup(
                                            type="ALL",
                                            criteria_list=[
                                                CorelatedCriteria(
                                                    criteria=ConditionOccurrence(codeset_id=4),
                                                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                                                    start_window=Window(
                                                        start=WindowBound(coeff=1, days=0),
                                                        end=WindowBound(coeff=1, days=5),
                                                        use_event_end=False,
                                                        use_index_end=False,
                                                    ),
                                                )
                                            ],
                                        ),
                                    ),
                                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                                    start_window=Window(
                                        start=WindowBound(coeff=1, days=0),
                                        end=WindowBound(coeff=1, days=5),
                                        use_event_end=False,
                                        use_index_end=False,
                                    ),
                                )
                            ],
                        ),
                    ),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                    start_window=Window(
                        start=WindowBound(coeff=1, days=0),
                        end=WindowBound(coeff=1, days=20),
                        use_event_end=False,
                        use_index_end=False,
                    ),
                )
            ],
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}


def test_primary_drug_era_correlated_era_length_is_applied():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "drug_era",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 2, 2],
                "drug_era_id": [1300, 1301, 2300, 2301],
                "drug_concept_id": [111, 222, 111, 222],
                "drug_era_start_date": ["2020-01-01", "2020-03-20", "2020-01-01", "2020-03-20"],
                "drug_era_end_date": ["2020-03-15", "2020-04-25", "2020-03-15", "2020-03-20"],
                "drug_exposure_count": [3, 1, 3, 1],
                "gap_days": [10, 0, 10, 0],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                DrugEra(
                    codeset_id=1,
                    era_length=NumericRange(op="gte", value=30),
                    correlated_criteria=CriteriaGroup(
                        type="ALL",
                        criteria_list=[
                            CorelatedCriteria(
                                criteria=DrugEra(
                                    codeset_id=2,
                                    era_length=NumericRange(op="gte", value=30),
                                ),
                                occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                                start_window=Window(
                                    start=WindowBound(coeff=1, days=0),
                                    end=WindowBound(coeff=1, days=60),
                                    use_event_end=False,
                                    use_index_end=True,
                                ),
                            )
                        ],
                    ),
                )
            ]
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    assert set(result.person_id) == {1}
