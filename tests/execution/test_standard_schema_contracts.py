from __future__ import annotations

import pytest

from circe.api import build_cohort_ibis
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.execution.plan.schema import STANDARD_EVENT_COLUMNS
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem
from tests.execution._assertions import assert_standard_event_columns


def test_standard_schema_constants_define_expected_column_order():
    assert STANDARD_EVENT_COLUMNS == (
        "person_id",
        "event_id",
        "start_date",
        "end_date",
        "domain",
        "concept_id",
        "source_concept_id",
        "visit_occurrence_id",
        "visit_detail_id",
        "quantity",
        "days_supply",
        "refills",
        "range_low",
        "range_high",
        "value_as_number",
        "unit_concept_id",
        "occurrence_count",
        "gap_days",
        "duration",
        "criterion_index",
        "criterion_type",
        "source_table",
    )


def test_standard_schema_contract_for_compiled_primary_events():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
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

    expression = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=111))]),
            )
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    assert_standard_event_columns(result.columns)
