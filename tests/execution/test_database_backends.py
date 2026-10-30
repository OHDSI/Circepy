"""Backend-agnostic execution contract for the HADES database platforms.

The suite always runs against DuckDB.  PostgreSQL, SQL Server, SQLite and the
cloud backends are enabled by exporting the corresponding ``CIRCE_TEST_*``
variables; the CI workflow starts PostgreSQL and SQL Server service containers
for the server job.  See ``docs/developer/database-testing.rst``.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    DateOffsetStrategy,
    InclusionRule,
    PrimaryCriteria,
)
from circe.cohortdefinition.core import NumericRange
from circe.execution.errors import ExecutionError
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem
from tests.execution._database_matrix import BackendHarness, live_backend_configs, open_backend

pytestmark = pytest.mark.integration


def _concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _expression(
    *,
    age_min: int | None = None,
    inclusion: bool = False,
    end_strategy: DateOffsetStrategy | None = None,
) -> CohortExpression:
    return CohortExpression(
        concept_sets=[_concept_set(1, 111), _concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(
                    codeset_id=1,
                    first=True,
                    age=NumericRange(op="gte", value=age_min) if age_min is not None else None,
                )
            ]
        ),
        inclusion_rules=[
            InclusionRule(
                name="has inclusion event",
                expression=CriteriaGroup(
                    type="ALL",
                    criteria_list=[CorelatedCriteria(criteria=ConditionOccurrence(codeset_id=2))],
                ),
            )
        ]
        if inclusion
        else [],
        end_strategy=end_strategy,
    )


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


@pytest.fixture(scope="module", params=live_backend_configs(), ids=lambda config: config.key)
def backend(request) -> BackendHarness:
    with open_backend(request.param) as harness:
        yield harness


def test_primary_criteria_with_age_filter(backend: BackendHarness):
    result = backend.build(_expression(age_min=18)).execute()

    assert set(result.columns) >= {
        "person_id",
        "event_id",
        "start_date",
        "end_date",
        "criterion_type",
    }
    # Person 2 is a child; person 3 has no inclusion event but the primary
    # criteria on its own should still return them.
    assert set(result["person_id"]) == {1, 3, 4}


def test_inclusion_rule_is_applied(backend: BackendHarness):
    result = backend.build(_expression(age_min=18, inclusion=True)).execute()

    assert set(result["person_id"]) == {1, 4}


def test_date_offset_end_strategy(backend: BackendHarness):
    expression = _expression(
        age_min=18,
        end_strategy=DateOffsetStrategy(date_field="StartDate", offset=30),
    )

    result = backend.build(expression).execute()

    ends = {
        int(person_id): _as_date(end_date)
        for person_id, end_date in zip(result["person_id"], result["end_date"], strict=True)
    }
    assert ends == {
        1: date(2020, 1, 31),
        3: date(2020, 2, 5),
        4: date(2020, 3, 31),
    }


def test_lazy_and_materialized_builds_return_the_same_events(backend: BackendHarness):
    expression = _expression(age_min=18, inclusion=True)

    lazy = backend.build(expression, materialize=False).execute()
    materialized = backend.build(expression, materialize=True).execute()

    columns = ["person_id", "event_id", "start_date", "end_date"]
    lazy_rows = lazy[columns].sort_values(["person_id", "event_id"]).reset_index(drop=True)
    materialized_rows = materialized[columns].sort_values(["person_id", "event_id"]).reset_index(drop=True)

    assert lazy_rows.equals(materialized_rows)


def test_write_cohort_fails_on_duplicates_and_replaces(backend: BackendHarness):
    expression = _expression(age_min=18, inclusion=True)

    backend.write(expression, cohort_table="cohort_out", cohort_id=42)
    written = backend.connection.table("cohort_out", database=backend.cdm_schema).execute()
    assert set(written["subject_id"]) == {1, 4}

    with pytest.raises(ExecutionError, match="already contains rows for cohort_id=42"):
        backend.write(expression, cohort_table="cohort_out", cohort_id=42)

    backend.write(expression, cohort_table="cohort_out", cohort_id=42, if_exists="replace")
    replaced = backend.connection.table("cohort_out", database=backend.cdm_schema).execute()
    assert len(replaced) == 2
    assert set(replaced["subject_id"]) == {1, 4}
