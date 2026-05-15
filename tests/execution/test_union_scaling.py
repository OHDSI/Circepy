"""Tests that cohort expression UNION ALL scales to large numbers of primary criteria.

Reproduces the failure mode where cohorts with 51-97 criteria (like
PhenotypeLibrary cohorts 1432-1434) crash DuckDB because the sequential
pairwise ``_union_all`` produces O(n) nesting depth.
"""

from __future__ import annotations

import pytest

from circe.cohort_definition_set import CohortDefinitionSet, generate_cohort_set
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def _seed_tables(conn, ibis, n_persons: int = 2):
    person_ids = list(range(1, n_persons + 1))
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": person_ids,
                "year_of_birth": [1980] * n_persons,
                "gender_concept_id": [8507] * n_persons,
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": person_ids,
                "observation_period_id": person_ids,
                "observation_period_start_date": ["2019-01-01"] * n_persons,
                "observation_period_end_date": ["2022-12-31"] * n_persons,
            }
        ),
        overwrite=True,
    )

    # Each person gets one condition row per concept_id from 1..N
    condition_rows = []
    for pid in person_ids:
        for cid in range(1, n_persons * 25 + 1):
            condition_rows.append(
                {
                    "person_id": pid,
                    "condition_occurrence_id": pid * 1000 + cid,
                    "condition_concept_id": cid,
                    "condition_start_date": "2020-01-10",
                    "condition_end_date": "2020-01-10",
                }
            )

    conn.create_table("condition_occurrence", obj=ibis.memtable(condition_rows), overwrite=True)

    # Minimal vocabulary (must have at least one non-None invalid_reason
    # so ibis can infer a non-NULL column type for DuckDB)
    concept_ids = list(range(1, n_persons * 25 + 1))
    invalid = [None] * len(concept_ids)
    if invalid:
        invalid[0] = "X"  # ensure type inference
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": concept_ids,
                "invalid_reason": invalid,
            }
        ),
        overwrite=True,
    )


def _build_multi_criterion_expression(n: int) -> CohortExpression:
    """Build a cohort with *n* simple ConditionOccurrence primary criteria."""
    concept_sets = []
    criteria = []
    for i in range(n):
        cs_id = i + 1
        concept_sets.append(_make_concept_set(cs_id, concept_id=cs_id))
        criteria.append(ConditionOccurrence(codeset_id=cs_id))
    return CohortExpression(concept_sets=concept_sets, primary_criteria=PrimaryCriteria(criteria_list=criteria))


@pytest.mark.parametrize("n_criteria", [1, 2, 5, 10, 20, 50, 100])
def test_union_all_scales(n_criteria: int) -> None:
    """Cohorts with N primary criteria should compile and execute without nesting errors."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_tables(conn, ibis)

    expression = _build_multi_criterion_expression(n_criteria)
    cds = CohortDefinitionSet()
    cds.add(1, f"UnionTest_{n_criteria}", expression)

    results = generate_cohort_set(
        cds,
        backend=conn,
        cdm_schema="main",
        cohort_table=f"union_test_{n_criteria}",
        stop_on_error=True,
    )

    assert len(results) == 1
    assert results[0].status == "COMPLETE", f"{n_criteria} criteria failed: {results[0].error}"
