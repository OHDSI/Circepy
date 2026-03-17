from __future__ import annotations

import pytest

from circe.api import build_cohort
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.cohortdefinition.core import CollapseSettings, DateOffsetStrategy, Period
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _seed_common_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "year_of_birth": [1980],
                "gender_concept_id": [8507],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "observation_period_id": [10],
                "observation_period_start_date": ["2019-01-01"],
                "observation_period_end_date": ["2021-12-31"],
            }
        ),
        overwrite=True,
    )


def test_date_offset_end_strategy_applies_to_end_date():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [100],
                "condition_concept_id": [111],
                "condition_start_date": ["2020-01-01"],
                "condition_end_date": ["2020-01-01"],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        end_strategy=DateOffsetStrategy(offset=30, date_field="start_date"),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert str(result.iloc[0]["end_date"])[:10] == "2020-01-31"


def test_censoring_criteria_clips_end_date():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "condition_occurrence_id": [100, 101],
                "condition_concept_id": [111, 222],
                "condition_start_date": ["2020-01-01", "2020-01-10"],
                "condition_end_date": ["2020-01-01", "2020-01-10"],
                "visit_occurrence_id": [10, 10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        censoring_criteria=[ConditionOccurrence(codeset_id=2)],
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert str(result.iloc[0]["end_date"])[:10] == "2020-01-10"


def test_censor_window_clips_start_and_end_dates():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [100],
                "condition_concept_id": [111],
                "condition_start_date": ["2020-01-01"],
                "condition_end_date": ["2020-01-01"],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        end_strategy=DateOffsetStrategy(offset=40, date_field="start_date"),
        censor_window=Period(start_date="2020-01-05", end_date="2020-01-20"),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert str(result.iloc[0]["start_date"])[:10] == "2020-01-05"
    assert str(result.iloc[0]["end_date"])[:10] == "2020-01-20"


def test_collapse_settings_era_merges_intervals():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "condition_occurrence_id": [100, 101],
                "condition_concept_id": [111, 111],
                "condition_start_date": ["2020-01-01", "2020-01-03"],
                "condition_end_date": ["2020-01-01", "2020-01-03"],
                "visit_occurrence_id": [10, 10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        end_strategy=DateOffsetStrategy(offset=0, date_field="start_date"),
        collapse_settings=CollapseSettings(era_pad=2),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.columns) == {"person_id", "start_date", "end_date"}
    assert len(result) == 1
    assert str(result.iloc[0]["start_date"])[:10] == "2020-01-01"
    assert str(result.iloc[0]["end_date"])[:10] == "2020-01-03"
