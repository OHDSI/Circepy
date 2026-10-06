from __future__ import annotations

import pytest

from circe.cohortdefinition import (
    CohortExpression,
    ConditionEra,
    CustomEra,
    Episode,
    NumericRange,
    PrimaryCriteria,
)
from circe.cohortdefinition.cohort_expression_query_builder import CohortExpressionQueryBuilder
from circe.cohortdefinition.printfriendly import MarkdownRender
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def test_episode_sql_builder():
    builder = CohortExpressionQueryBuilder()
    sql = builder.get_criteria_sql(Episode(codeset_id=1, first=True))
    assert "-- Begin Episode Criteria" in sql
    assert "FROM @cdm_database_schema.EPISODE ep" in sql
    assert "C.episode_id as event_id" in sql


def test_custom_era_sql_builder():
    builder = CohortExpressionQueryBuilder()
    criteria = CustomEra(
        criteria_list=[ConditionEra(codeset_id=1), ConditionEra(codeset_id=2)],
        gap_days=60,
    )
    sql = builder.get_criteria_sql(criteria)
    assert "sum(is_start)" in sql
    assert "@eraconstructorpad" not in sql
    assert "@criteriaQueries" not in sql
    assert "UNION ALL" in sql


def test_episode_and_custom_era_roundtrip_json():
    criteria = Episode(codeset_id=1, first=True, episode_number=NumericRange(op="gt", value=2))
    raw = criteria.model_dump_json(by_alias=True, exclude_none=True)
    assert '"Episode"' in raw

    custom = CustomEra(criteria_list=[ConditionEra(codeset_id=1)], gap_days=60)
    raw = custom.model_dump_json(by_alias=True, exclude_none=True)
    assert '"CustomEra"' in raw
    assert '"GapDays":60' in raw


def test_markdown_renders_episode_and_custom_era():
    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                Episode(codeset_id=1, first=True),
                CustomEra(criteria_list=[ConditionEra(codeset_id=1)], gap_days=60),
            ]
        )
    )
    markdown = MarkdownRender().render_cohort_expression(expression)
    assert "episode" in markdown
    assert "custom era" in markdown
    assert "60-day gap" in markdown


def test_build_cohort_episode():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {"person_id": [1, 2], "year_of_birth": [1980, 2015], "gender_concept_id": [8507, 8507]}
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
                "episode_concept_id": [7777, 9999],
                "episode_number": [1, 1],
                "episode_object_concept_id": [0, 0],
                "episode_type_concept_id": [0, 0],
                "episode_start_date": ["2020-03-01", "2020-03-01"],
                "episode_end_date": ["2020-04-01", "2020-04-01"],
            }
        ),
        overwrite=True,
    )

    from circe.api import build_cohort

    expression = CohortExpression(
        concept_sets=[_make_concept_set(12, 7777)],
        primary_criteria=PrimaryCriteria(criteria_list=[Episode(codeset_id=12)]),
    )
    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "episode")


def test_compile_custom_era_collapses_gap():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    from circe.execution.ibis.compiler import compile_event_plan
    from circe.execution.ibis.context import make_execution_context
    from circe.execution.lower.criteria import lower_criterion
    from circe.execution.normalize.criteria import normalize_criterion

    conn = ibis.duckdb.connect()
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
    codesets = ibis.memtable({"codeset_id": [1, 2], "concept_id": [5, 6]})
    ctx = make_execution_context(backend=conn, cdm_schema="main", codeset_table=codesets)

    merged = normalize_criterion(
        CustomEra(criteria_list=[ConditionEra(codeset_id=1), ConditionEra(codeset_id=2)], gap_days=60)
    )
    plan = lower_criterion(merged, criterion_index=1)
    result = compile_event_plan(plan, ctx).execute()
    assert len(result) == 1
    assert result.iloc[0]["start_date"].date().isoformat() == "2020-01-01"
    assert result.iloc[0]["end_date"].date().isoformat() == "2020-03-15"

    separate = normalize_criterion(
        CustomEra(criteria_list=[ConditionEra(codeset_id=1), ConditionEra(codeset_id=2)], gap_days=30)
    )
    plan = lower_criterion(separate, criterion_index=1)
    result = compile_event_plan(plan, ctx).execute()
    assert len(result) == 2
