from __future__ import annotations

import pytest

from circe.api import build_cohort
from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    DemographicCriteria,
    Occurrence,
    PrimaryCriteria,
)
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _seed_common_tables(conn, ibis, *, persons):
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


def test_parity_concept_set_expansion_with_exclusions():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2))
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [100, 101, 102, 200, 201],
                "invalid_reason": [None, None, "D", None, None],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable(
            {
                "ancestor_concept_id": [100, 100],
                "descendant_concept_id": [101, 102],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable(
            {
                "concept_id_1": [200, 201],
                "concept_id_2": [100, 101],
                "relationship_id": ["Maps to", "Maps to"],
                "invalid_reason": [None, "D"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 2],
                "condition_occurrence_id": [1000, 1001, 1002, 1003],
                "condition_concept_id": [100, 101, 200, 999],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-01",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-01",
                ],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    items=[
                        ConceptSetItem(
                            concept=Concept(conceptId=100),
                            includeDescendants=True,
                            includeMapped=True,
                        ),
                        ConceptSetItem(
                            concept=Concept(conceptId=101),
                            isExcluded=True,
                            includeMapped=True,
                        ),
                    ]
                ),
            )
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}
    assert set(result.concept_id) == {100, 200}


def test_parity_primary_correlated_and_demographic_group_combination():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis, persons=(1, 2, 3))
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "year_of_birth": [1980, 1980, 1980],
                "gender_concept_id": [8507, 8507, 8507],
                "race_concept_id": [8527, 8527, 8516],
                "ethnicity_concept_id": [38003564, 38003564, 38003564],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 2, 3, 3],
                "condition_occurrence_id": [10, 11, 20, 30, 31],
                "condition_concept_id": [111, 222, 111, 111, 222],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-03",
                    "2020-01-01",
                    "2020-01-01",
                    "2020-01-03",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-03",
                    "2020-01-01",
                    "2020-01-01",
                    "2020-01-03",
                ],
                "visit_occurrence_id": [10, 10, 20, 30, 30],
            }
        ),
        overwrite=True,
    )

    primary = ConditionOccurrence(
        codeset_id=1,
        correlated_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=2),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                )
            ],
        ),
    )
    expression = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=111))]),
            ),
            ConceptSet(
                id=2,
                expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=222))]),
            ),
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[primary]),
        additional_criteria=CriteriaGroup(
            type="ALL",
            demographic_criteria_list=[
                DemographicCriteria(
                    race=[Concept(conceptId=8527)],
                    ethnicity=[Concept(conceptId=38003564)],
                )
            ],
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}
