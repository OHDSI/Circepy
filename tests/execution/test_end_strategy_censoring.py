from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from circe.api import build_cohort
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.cohortdefinition.core import CollapseSettings, CustomEraStrategy, DateOffsetStrategy, Period
from circe.execution.engine.end_strategy import apply_end_strategy
from circe.execution.errors import UnsupportedFeatureError
from circe.execution.normalize.end_strategy import NormalizedEndStrategy
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


def test_apply_end_strategy_rejects_invalid_date_field_and_preserves_fallback_semantics():
    ibis_mod = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis_mod.duckdb.connect()
    conn.create_table(
        "events",
        obj=ibis_mod.memtable(
            {
                "person_id": [1],
                "event_id": [100],
                "start_date": [date(2020, 1, 1)],
                "end_date": [date(2020, 1, 5)],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis_mod.memtable(
            {
                "person_id": [1],
                "observation_period_start_date": [date(2019, 1, 1)],
                "observation_period_end_date": [date(2020, 1, 10)],
            }
        ),
        overwrite=True,
    )
    ctx = SimpleNamespace(table=lambda name: conn.table(name))
    events = conn.table("events")

    with pytest.raises(UnsupportedFeatureError, match="unsupported date_offset date field"):
        apply_end_strategy(
            events,
            NormalizedEndStrategy(kind="date_offset", payload={"offset": 1, "date_field": "weird"}),
            ctx,
        ).execute()

    fallback = apply_end_strategy(events, NormalizedEndStrategy(kind="unknown", payload={}), ctx).execute()
    assert str(fallback.iloc[0]["end_date"])[:10] == "2020-01-10"


def test_custom_era_end_strategy_uses_drug_exposure_eras():
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
                "condition_start_date": ["2020-01-10"],
                "condition_end_date": ["2020-01-10"],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "drug_exposure_id": [200, 201],
                "drug_concept_id": [222, 222],
                "drug_source_concept_id": [222, 222],
                "drug_exposure_start_date": ["2020-01-01", "2020-01-10"],
                "drug_exposure_end_date": ["2020-01-05", "2020-01-12"],
                "days_supply": [0, 0],
                "visit_occurrence_id": [10, 10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        end_strategy=CustomEraStrategy(drug_codeset_id=2, gap_days=7, offset=0),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert str(result.iloc[0]["end_date"])[:10] == "2020-01-12"


def test_custom_era_end_strategy_falls_back_to_observation_end_when_no_matching_exposure():
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
                "condition_start_date": ["2020-01-10"],
                "condition_end_date": ["2020-01-10"],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "drug_exposure_id": [200],
                "drug_concept_id": [222],
                "drug_source_concept_id": [222],
                "drug_exposure_start_date": ["2019-01-01"],
                "drug_exposure_end_date": ["2019-01-05"],
                "days_supply": [0],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        end_strategy=CustomEraStrategy(drug_codeset_id=2, gap_days=7, offset=0),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert str(result.iloc[0]["end_date"])[:10] == "2021-12-31"


def test_custom_era_days_supply_override_changes_exposure_end():
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
                "condition_start_date": ["2020-01-03"],
                "condition_end_date": ["2020-01-03"],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "drug_exposure_id": [200],
                "drug_concept_id": [222],
                "drug_source_concept_id": [222],
                "drug_exposure_start_date": ["2020-01-01"],
                "drug_exposure_end_date": ["2020-01-31"],
                "days_supply": [30],
                "visit_occurrence_id": [10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
        end_strategy=CustomEraStrategy(
            drug_codeset_id=2,
            gap_days=0,
            offset=0,
            days_supply_override=2,
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert str(result.iloc[0]["end_date"])[:10] == "2020-01-03"
