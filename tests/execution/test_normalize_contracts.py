from __future__ import annotations

import pytest

from circe.cohortdefinition import CohortExpression, PrimaryCriteria
from circe.execution.normalize.cohort import normalize_cohort
from circe.execution.normalize.criteria import normalize_criterion
from circe.execution.normalize.groups import NormalizedCriteriaGroup
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

from tests.execution._domain_cases import domain_criteria_cases


@pytest.mark.parametrize(("source_table", "factory", "_"), domain_criteria_cases())
def test_normalize_criterion_contract(source_table, factory, _):
    criteria = factory()
    normalized = normalize_criterion(criteria)

    assert normalized.criterion_type == criteria.__class__.__name__
    assert normalized.source_table == source_table
    assert normalized.domain
    assert normalized.event_id_column
    assert normalized.start_date_column
    assert normalized.end_date_column


@pytest.mark.parametrize(("source_table", "factory", "concept_id"), domain_criteria_cases())
def test_normalize_cohort_does_not_mutate_public_expression(
    source_table,
    factory,
    concept_id,
):
    del source_table

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
    before = expression.model_dump_json(by_alias=True, exclude_none=False)

    normalized = normalize_cohort(expression)
    after = expression.model_dump_json(by_alias=True, exclude_none=False)

    assert before == after
    assert len(normalized.primary.criteria) == 1
    assert isinstance(normalized.additional_criteria, (type(None), NormalizedCriteriaGroup))
