from __future__ import annotations

import pytest

from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


@pytest.fixture
def ibis_duckdb_conn():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")
    return ibis, ibis.duckdb.connect()


def make_expression(concept_id: int = 111) -> CohortExpression:
    return CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
                ),
            )
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )


def seed_base_tables(ibis, conn, concept_id: int = 111, rows: int = 2) -> None:
    person_ids = [i + 1 for i in range(rows)]
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": person_ids,
                "year_of_birth": [1980 for _ in person_ids],
                "gender_concept_id": [8507 for _ in person_ids],
                "race_concept_id": [8527 for _ in person_ids],
                "ethnicity_concept_id": [38003563 for _ in person_ids],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": person_ids,
                "observation_period_id": [100 + i for i in range(rows)],
                "observation_period_start_date": ["2019-01-01" for _ in person_ids],
                "observation_period_end_date": ["2021-12-31" for _ in person_ids],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": person_ids,
                "condition_occurrence_id": [1000 + i for i in range(rows)],
                "condition_concept_id": [concept_id for _ in person_ids],
                "condition_start_date": ["2020-01-01" for _ in person_ids],
                "condition_end_date": ["2020-01-01" for _ in person_ids],
            }
        ),
        overwrite=True,
    )


def seed_generated_cohort_table(
    ibis,
    conn,
    *,
    rows: list[dict],
    table_name: str = "cohort",
    schema: str = "main",
) -> None:
    conn.create_table(
        table_name,
        obj=ibis.memtable(
            {
                "cohort_definition_id": [int(row["cohort_definition_id"]) for row in rows],
                "subject_id": [int(row["subject_id"]) for row in rows],
                "cohort_start_date": [row["cohort_start_date"] for row in rows],
                "cohort_end_date": [row["cohort_end_date"] for row in rows],
            }
        ),
        database=schema,
        overwrite=True,
    )
