from __future__ import annotations

import pytest

from circe.api import build_cohort_ibis
from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaColumn,
    CriteriaGroup,
    Occurrence,
    PrimaryCriteria,
    VisitDetail,
)
from circe.cohortdefinition.core import ResultLimit
from circe.execution import api as execution_api
from circe.execution.engine.group_operators import resolve_distinct_count_column
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
                "observation_period_end_date": ["2022-12-31"],
            }
        ),
        overwrite=True,
    )


def test_primary_limit_last_keeps_latest_primary_event():
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
                "condition_start_date": ["2020-01-01", "2020-02-01"],
                "condition_end_date": ["2020-01-01", "2020-02-01"],
                "visit_occurrence_id": [10, 10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
            primary_limit=ResultLimit(type="LAST"),
        ),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    assert len(result) == 1
    assert str(result.iloc[0]["start_date"])[:10] == "2020-02-01"


def test_expression_limit_last_keeps_latest_qualified_event():
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
                "condition_start_date": ["2020-01-01", "2020-02-01"],
                "condition_end_date": ["2020-01-01", "2020-02-01"],
                "visit_occurrence_id": [10, 10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
            primary_limit=ResultLimit(type="ALL"),
        ),
        expression_limit=ResultLimit(type="LAST"),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    assert len(result) == 1
    assert str(result.iloc[0]["start_date"])[:10] == "2020-02-01"


def test_qualified_limit_last_applies_after_additional_criteria():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 1],
                "condition_occurrence_id": [100, 101, 102, 103],
                "condition_concept_id": [111, 111, 222, 222],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-02-01",
                    "2020-01-02",
                    "2020-02-02",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-02-01",
                    "2020-01-02",
                    "2020-02-02",
                ],
                "visit_occurrence_id": [10, 10, 10, 10],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
            primary_limit=ResultLimit(type="ALL"),
        ),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=2),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                    restrict_visit=True,
                )
            ],
        ),
        qualified_limit=ResultLimit(type="LAST"),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    assert len(result) == 1
    assert str(result.iloc[0]["start_date"])[:10] == "2020-02-01"


def test_write_cohort_without_results_schema_uses_backend_default(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_build_cohort(*args, **kwargs):
        return object()

    def _fake_project_to_ohdsi_cohort_table(relation, *, cohort_id):
        return relation

    def _fake_table_exists(*args, **kwargs):
        return False

    def _fake_write_relation(
        relation, *, backend, target_table, target_schema=None, if_exists="fail", temporary=False
    ):
        backend.create_table(target_table, obj=relation, overwrite=(if_exists == "replace"))

    class _Backend:
        def create_table(self, name, **kwargs):
            captured["name"] = name
            captured["kwargs"] = kwargs

    monkeypatch.setattr(execution_api, "build_cohort", _fake_build_cohort)
    monkeypatch.setattr(
        execution_api,
        "project_to_ohdsi_cohort_table",
        _fake_project_to_ohdsi_cohort_table,
    )
    monkeypatch.setattr(execution_api, "table_exists", _fake_table_exists)
    monkeypatch.setattr(execution_api, "write_relation", _fake_write_relation)

    execution_api.write_cohort(
        CohortExpression(primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence()])),
        backend=_Backend(),
        cdm_schema="cdm",
        cohort_table="cohort_out",
        cohort_id=1,
    )

    assert captured["name"] == "cohort_out"
    assert "database" not in captured["kwargs"]


@pytest.mark.parametrize(
    "count_column",
    [
        None,
        CriteriaColumn.DOMAIN_CONCEPT,
        CriteriaColumn.DOMAIN_SOURCE_CONCEPT,
        CriteriaColumn.VISIT_ID,
        CriteriaColumn.VISIT_DETAIL_ID,
        CriteriaColumn.START_DATE,
        CriteriaColumn.END_DATE,
        CriteriaColumn.DURATION,
        CriteriaColumn.QUANTITY,
        CriteriaColumn.DAYS_SUPPLY,
        CriteriaColumn.REFILLS,
        CriteriaColumn.RANGE_LOW,
        CriteriaColumn.RANGE_HIGH,
        CriteriaColumn.VALUE_AS_NUMBER,
        CriteriaColumn.UNIT,
        CriteriaColumn.ERA_OCCURRENCES,
        CriteriaColumn.GAP_DAYS,
    ],
)
def test_resolve_distinct_count_column_supports_public_count_columns(count_column):
    resolved = resolve_distinct_count_column(None if count_column is None else count_column.value)
    assert resolved.startswith("a_")


def test_distinct_count_by_visit_detail_id_matches_sql_semantics():
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
    conn.create_table(
        "visit_detail",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "visit_detail_id": [200, 201],
                "visit_detail_concept_id": [222, 222],
                "visit_detail_start_date": ["2020-01-01", "2020-01-01"],
                "visit_detail_end_date": ["2020-01-02", "2020-01-02"],
                "visit_occurrence_id": [10, 10],
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
                    criteria=VisitDetail(codeset_id=2),
                    occurrence=Occurrence(
                        type=Occurrence._AT_LEAST,
                        count=2,
                        is_distinct=True,
                        count_column=CriteriaColumn.VISIT_DETAIL_ID,
                    ),
                    restrict_visit=True,
                )
            ],
        ),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    assert len(result) == 1
