from __future__ import annotations

from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    DrugExposure,
    ObservationFilter,
    Occurrence,
    PrimaryCriteria,
    ResultLimit,
)
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def concept_set(concept_id: int, set_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        name=f"concept_{concept_id}",
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(concept_id=concept_id))]),
    )


def condition_cohort(
    concept_id: int,
    name: str,
    *,
    set_id: int = 1,
) -> CohortExpression:
    return CohortExpression(
        title=name,
        concept_sets=[concept_set(concept_id, set_id)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=set_id)],
            observation_window=ObservationFilter(prior_days=0, post_days=0),
            primary_limit=ResultLimit(type="All"),
        ),
    )


def drug_cohort(concept_id: int, name: str, *, set_id: int = 1) -> CohortExpression:
    return CohortExpression(
        title=name,
        concept_sets=[concept_set(concept_id, set_id)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[DrugExposure(codeset_id=set_id)],
            observation_window=ObservationFilter(prior_days=0, post_days=0),
            primary_limit=ResultLimit(type="All"),
        ),
    )


def drug_criteria_group(*, codeset_id: int = 2) -> CriteriaGroup:
    return CriteriaGroup(
        criteria_list=[
            CorelatedCriteria(
                criteria=DrugExposure(codeset_id=codeset_id),
                occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
            )
        ],
        type="ALL",
    )
