from __future__ import annotations

import pytest

from circe.cohortdefinition import CohortExpression, PrimaryCriteria
from circe.execution.ibis.compiler import compile_event_plan
from circe.execution.ibis.context import make_execution_context
from circe.execution.lower.criteria import lower_criterion
from circe.execution.normalize.cohort import normalize_cohort
from circe.execution.plan.schema import STANDARD_EVENT_COLUMNS
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

from tests.execution._domain_cases import domain_criteria_cases


def _seed_common_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "year_of_birth": [1980],
                "gender_concept_id": [8507],
                "race_concept_id": [8527],
                "ethnicity_concept_id": [38003564],
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


@pytest.mark.parametrize(("source_table", "factory", "concept_id"), domain_criteria_cases())
def test_compile_contract_emits_standard_schema(source_table, factory, concept_id):
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    criteria = factory()
    concept_sets = []
    if concept_id is not None:
        concept_sets = [
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
                ),
            )
        ]

    expression = CohortExpression(
        concept_sets=concept_sets,
        primary_criteria=PrimaryCriteria(criteria_list=[criteria]),
    )
    normalized = normalize_cohort(expression)
    normalized_criterion = normalized.primary.criteria[0]
    plan = lower_criterion(normalized_criterion, criterion_index=0)

    source_data = {
        plan.source.person_id_column: [1],
        plan.source.event_id_column: [101],
        plan.source.start_date_column: ["2020-01-01"],
        plan.source.end_date_column: ["2020-01-01"],
    }
    if plan.source.visit_occurrence_column and plan.source.visit_occurrence_column not in source_data:
        source_data[plan.source.visit_occurrence_column] = [10]
    if (
        plan.source.concept_column
        and plan.source.concept_column not in source_data
        and source_table != "location_history"
    ):
        source_data[plan.source.concept_column] = [concept_id or 0]
    if (
        plan.source.source_concept_column
        and plan.source.source_concept_column not in source_data
    ):
        source_data[plan.source.source_concept_column] = [concept_id or 0]
    if source_table == "location_history":
        source_data["domain_id"] = ["PERSON"]
        source_data["location_id"] = [10]
        conn.create_table(
            "location",
            obj=ibis.memtable({"location_id": [10], "region_concept_id": [concept_id]}),
            overwrite=True,
        )

    conn.create_table(source_table, obj=ibis.memtable(source_data), overwrite=True)

    ctx = make_execution_context(
        backend=conn,
        cdm_schema="main",
        results_schema=None,
        options=None,
        concept_sets=normalized.concept_sets,
    )

    result = compile_event_plan(plan, ctx).execute()
    assert tuple(result.columns) == STANDARD_EVENT_COLUMNS
    assert len(result) == 1
