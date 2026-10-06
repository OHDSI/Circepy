"""Coverage-focused tests for the Episode and CustomEra criteria additions."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from circe.check.checkers.criteria_checker_factory import CriteriaCheckerFactory
from circe.check.checkers.range_checker_factory import RangeCheckerFactory
from circe.cohortdefinition import (
    CohortExpression,
    ConditionEra,
    CustomEra,
    Episode,
    NumericRange,
    PrimaryCriteria,
)
from circe.cohortdefinition.builders.custom_era import CustomEraSqlBuilder
from circe.cohortdefinition.builders.episode import EpisodeSqlBuilder
from circe.cohortdefinition.builders.utils import BuilderOptions, CriteriaColumn
from circe.cohortdefinition.cohort_expression_query_builder import CohortExpressionQueryBuilder
from circe.cohortdefinition.core import (
    ConceptSetSelection,
    DateAdjustment,
    DateRange,
    DateType,
)
from circe.vocabulary import ConceptSet


# ---------------------------------------------------------------------------
# SQL builders
# ---------------------------------------------------------------------------


def test_episode_builder_full_logic():
    builder = EpisodeSqlBuilder()
    criteria = Episode(
        codeset_id=1,
        first=True,
        episode_start_date=DateRange(op="gt", value="2020-01-01"),
        episode_end_date=DateRange(op="lt", value="2021-01-01"),
        episode_number=NumericRange(op="gte", value=2),
        age=NumericRange(op="gte", value=18),
        gender_cs=ConceptSetSelection(codeset_id=2),
        episode_object_concept_cs=ConceptSetSelection(codeset_id=3),
        episode_type_cs=ConceptSetSelection(codeset_id=4),
        date_adjustment=DateAdjustment(
            startOffset=1, endOffset=2, startWith=DateType.START_DATE, endWith=DateType.END_DATE
        ),
    )
    sql = builder.get_criteria_sql(criteria)

    assert "FROM @cdm_database_schema.EPISODE ep" in sql
    assert "row_number() over (PARTITION BY ep.person_id" in sql
    assert "JOIN @cdm_database_schema.PERSON P" in sql
    assert "C.episode_number >= 2" in sql
    assert "YEAR(C.start_date) - P.year_of_birth >= 18" in sql
    assert "P.gender_concept_id" in sql
    assert "C.episode_object_concept_id" in sql
    assert "C.episode_type_concept_id" in sql
    assert "DATEADD(day,1, ep.episode_start_date)" in sql


def test_episode_builder_additional_columns():
    builder = EpisodeSqlBuilder()
    options = BuilderOptions()
    options.additional_columns = [CriteriaColumn.DURATION, CriteriaColumn.QUANTITY]

    sql = builder.get_criteria_sql_with_options(Episode(codeset_id=1), options)

    assert "DATEDIFF(d, C.start_date, C.end_date) as duration" in sql
    assert "NULL as quantity" in sql
    assert builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT) == (
        "C.episode_concept_id"
    )


def test_custom_era_builder_full_logic():
    builder = CustomEraSqlBuilder()
    criteria = CustomEra(
        criteria_list=[ConditionEra(codeset_id=1), ConditionEra(codeset_id=2)],
        first=True,
        gap_days=30,
        start_date=DateRange(op="gt", value="2020-01-01"),
        end_date=DateRange(op="lt", value="2021-01-01"),
        age_at_start=NumericRange(op="gte", value=18),
        gender_cs=ConceptSetSelection(codeset_id=5),
        duration=NumericRange(op="gte", value=10),
        date_adjustment=DateAdjustment(
            startOffset=0, endOffset=0, startWith=DateType.END_DATE, endWith=DateType.START_DATE
        ),
    )
    sql = builder.get_criteria_sql_with_options(criteria, None, criteria_query="SELECT 1")

    assert "row_number() over (PARTITION BY E.person_id" in sql
    assert "JOIN @cdm_database_schema.PERSON P" in sql
    assert "C.start_date > DATEFROMPARTS(2020, 1, 1)" in sql
    assert "C.end_date < DATEFROMPARTS(2021, 1, 1)" in sql
    assert "YEAR(C.start_date) - P.year_of_birth >= 18" in sql
    assert "P.gender_concept_id" in sql
    assert "DATEDIFF(d,C.start_date, C.end_date) >= 10" in sql
    assert "DATEADD(day,0, E.end_date)" in sql


def test_custom_era_builder_missing_criteria_query():
    builder = CustomEraSqlBuilder()
    sql = builder.get_criteria_sql_with_options(CustomEra(criteria_list=[ConditionEra(codeset_id=1)]), None)
    assert "@criteriaQueries" in sql


def test_custom_era_builder_table_columns():
    builder = CustomEraSqlBuilder()
    assert builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION) == (
        "DATEDIFF(d, C.start_date, C.end_date)"
    )
    assert builder.get_table_column_for_criteria_column(CriteriaColumn.QUANTITY) == "NULL"


def test_custom_era_empty_criteria_raises():
    builder = CohortExpressionQueryBuilder()
    with pytest.raises(RuntimeError, match="CriteriaList can not be null or empty"):
        builder.get_criteria_sql(CustomEra(criteria_list=[]))


def test_custom_era_sql_uses_nested_criteria():
    builder = CohortExpressionQueryBuilder()
    sql = builder.get_criteria_sql(
        CustomEra(criteria_list=[ConditionEra(codeset_id=1), ConditionEra(codeset_id=2)])
    )
    assert "UNION ALL" in sql
    assert sql.count("-- Begin Condition Era Criteria") == 2


# ---------------------------------------------------------------------------
# Model deserialization
# ---------------------------------------------------------------------------


def test_custom_era_deserializes_nested_criteria_variants():
    custom_era = CustomEra.model_validate(
        {
            "CriteriaList": [
                {"ConditionEra": {"CodesetId": 1}},
                {"Measurement": {}},
                {"Observation": {}},
                {"ConditionOccurrence": {}},
                {"conditionEra": {"CodesetId": 2}},
            ],
            "GapDays": 45,
        }
    )

    assert [type(c).__name__ for c in custom_era.criteria_list] == [
        "ConditionEra",
        "Measurement",
        "Observation",
        "ConditionOccurrence",
        "ConditionEra",
    ]
    assert custom_era.gap_days == 45


def test_custom_era_none_criteria_list_becomes_empty():
    custom_era = CustomEra.model_validate({"CriteriaList": None})
    assert custom_era.criteria_list == []


def test_custom_era_malformed_criteria_falls_back_gracefully():
    custom_era = CustomEra.model_validate({"CriteriaList": [{"ConditionEra": {"CodesetId": "bad"}}]})
    assert len(custom_era.criteria_list) == 1


def test_exchange_polymorphic_roundtrip():
    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                Episode(codeset_id=1, first=True),
                CustomEra(criteria_list=[ConditionEra(codeset_id=1)], gap_days=30),
            ]
        )
    )
    dumped = expression.model_dump(by_alias=True, exclude_none=True)
    criteria_list = dumped["PrimaryCriteria"]["CriteriaList"]
    assert "Episode" in criteria_list[0]
    assert "CustomEra" in criteria_list[1]

    restored = CohortExpression.model_validate(dumped)
    assert isinstance(restored.primary_criteria.criteria_list[0], Episode)
    assert isinstance(restored.primary_criteria.criteria_list[1], CustomEra)


# ---------------------------------------------------------------------------
# Check framework
# ---------------------------------------------------------------------------


def test_criteria_checker_factory_episode_and_custom_era():
    concept_set = ConceptSet(id=3, name="cs", expression=None)
    factory = CriteriaCheckerFactory(concept_set)

    object_episode = Episode(episode_object_concept_cs=ConceptSetSelection(codeset_id=3))
    assert factory.get_criteria_checker(object_episode)(object_episode) is True

    type_episode = Episode(episode_type_cs=ConceptSetSelection(codeset_id=3))
    assert factory.get_criteria_checker(type_episode)(type_episode) is True

    unrelated_episode = Episode(codeset_id=999)
    assert factory.get_criteria_checker(unrelated_episode)(unrelated_episode) is False

    nested_match = CustomEra(criteria_list=[ConditionEra(codeset_id=3)])
    assert factory.get_criteria_checker(nested_match)(nested_match) is True

    nested_miss = CustomEra(criteria_list=[ConditionEra(codeset_id=999)])
    assert factory.get_criteria_checker(nested_miss)(nested_miss) is False


def test_range_checker_factory_episode_and_custom_era():
    factory = RangeCheckerFactory(Mock(), "Test Group")

    factory.check(
        Episode(
            episode_start_date=DateRange(op="bt", value="2020-01-01", extent="2020-02-01"),
            episode_end_date=DateRange(op="gt", value="2020-03-01"),
            episode_number=NumericRange(op="gte", value=1),
            age=NumericRange(op="gte", value=18),
        )
    )
    factory.check(
        CustomEra(
            criteria_list=[ConditionEra(codeset_id=1)],
            start_date=DateRange(op="gt", value="2020-01-01"),
            end_date=DateRange(op="lt", value="2021-01-01"),
            age_at_start=NumericRange(op="gte", value=18),
            duration=NumericRange(op="gte", value=10),
        )
    )


# ---------------------------------------------------------------------------
# Ibis execution
# ---------------------------------------------------------------------------


def _build_ctx(conn, ibis, codeset_rows):
    from circe.execution.ibis.context import make_execution_context

    return make_execution_context(
        backend=conn,
        cdm_schema="main",
        codeset_table=ibis.memtable(codeset_rows),
    )


def test_compile_custom_era_applies_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    from circe.execution.ibis.compiler import compile_event_plan
    from circe.execution.lower.criteria import lower_criterion
    from circe.execution.normalize.criteria import normalize_criterion

    conn = ibis.duckdb.connect()
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {"person_id": [1], "year_of_birth": [1980], "gender_concept_id": [8507]}
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_era",
        obj=ibis.memtable(
            {
                "condition_era_id": [1, 2],
                "person_id": [1, 1],
                "condition_concept_id": [5, 6],
                "condition_occurrence_count": [1, 1],
                "condition_era_start_date": ["2020-01-01", "2020-03-05"],
                "condition_era_end_date": ["2020-01-15", "2020-03-15"],
            }
        ),
        overwrite=True,
    )
    ctx = _build_ctx(
        conn,
        ibis,
        {"codeset_id": [1, 2, 3], "concept_id": [5, 6, 8507]},
    )

    criteria = CustomEra(
        criteria_list=[ConditionEra(codeset_id=1), ConditionEra(codeset_id=2)],
        gap_days=60,
        gender_cs=ConceptSetSelection(codeset_id=3),
        age_at_start=NumericRange(op="gte", value=18),
        start_date=DateRange(op="gte", value="2019-01-01"),
        end_date=DateRange(op="lte", value="2021-01-01"),
        duration=NumericRange(op="gte", value=10),
        first=True,
    )
    plan = lower_criterion(normalize_criterion(criteria), criterion_index=1)
    result = compile_event_plan(plan, ctx).execute()

    assert len(result) == 1
    assert result.iloc[0]["source_table"] == "custom_era"


def test_compile_custom_era_empty_raises():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    from circe.execution.ibis.compiler import compile_event_plan
    from circe.execution.lower.criteria import lower_criterion
    from circe.execution.normalize.criteria import normalize_criterion

    conn = ibis.duckdb.connect()
    ctx = _build_ctx(conn, ibis, {"codeset_id": [1], "concept_id": [5]})

    plan = lower_criterion(normalize_criterion(CustomEra(criteria_list=[])), criterion_index=1)
    with pytest.raises(Exception, match="CriteriaList can not be null or empty"):
        compile_event_plan(plan, ctx)


def test_build_cohort_episode_with_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    from circe.api import build_cohort

    conn = ibis.duckdb.connect()
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {"person_id": [1, 2], "year_of_birth": [1980, 1980], "gender_concept_id": [8507, 8507]}
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
        "episode",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "episode_id": [500, 501],
                "episode_concept_id": [7777, 7777],
                "episode_number": [3, 1],
                "episode_object_concept_id": [11, 12],
                "episode_type_concept_id": [21, 22],
                "episode_start_date": ["2020-03-01", "2020-03-01"],
                "episode_end_date": ["2020-04-01", "2020-04-01"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            _concept_set(1, 7777),
            _concept_set(2, 11),
            _concept_set(3, 21),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                Episode(
                    codeset_id=1,
                    episode_number=NumericRange(op="gte", value=2),
                    episode_object_concept_cs=ConceptSetSelection(codeset_id=2),
                    episode_type_cs=ConceptSetSelection(codeset_id=3),
                )
            ]
        ),
    )
    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    assert set(result.person_id) == {1}


def _concept_set(set_id, concept_id):
    from circe.vocabulary import Concept, ConceptSetExpression, ConceptSetItem

    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(
            items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
        ),
    )
