from __future__ import annotations

from circe.cohortdefinition import (
    ConditionEra,
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    Death,
    DeviceExposure,
    DoseEra,
    DrugEra,
    InclusionRule,
    LocationRegion,
    Measurement,
    Observation,
    ObservationPeriod,
    Occurrence,
    PayerPlanPeriod,
    PrimaryCriteria,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
)
from circe.execution.normalize.criteria import normalize_criterion
from circe.cohortdefinition.core import NumericRange
from circe.execution.normalize.cohort import normalize_cohort
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _concept_set(set_id: int, include: int, exclude: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(concept=Concept(conceptId=include), isExcluded=False),
                ConceptSetItem(concept=Concept(conceptId=exclude), isExcluded=True),
            ]
        ),
    )


def test_normalize_cohort_extracts_codesets_and_keeps_expression_immutable():
    expression = CohortExpression(
        title="Normalize Test",
        concept_sets=[_concept_set(1, include=111, exclude=999)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(
                    codeset_id=1,
                    first=True,
                    age=NumericRange(op="gte", value=18),
                )
            ]
        ),
    )
    before = expression.model_dump_json(by_alias=True, exclude_none=False)

    normalized = normalize_cohort(expression)

    after = expression.model_dump_json(by_alias=True, exclude_none=False)
    assert before == after
    assert normalized.title == "Normalize Test"
    assert normalized.concept_sets[1] == frozenset({111})
    assert len(normalized.primary.criteria) == 1
    criterion = normalized.primary.criteria[0]
    assert criterion.criterion_type == "ConditionOccurrence"
    assert criterion.codeset_id == 1
    assert criterion.first is True
    assert criterion.person_filters.age is not None


def test_normalize_cohort_additional_criteria_group():
    expression = CohortExpression(
        concept_sets=[_concept_set(1, include=111, exclude=999)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
        additional_criteria=CriteriaGroup(
            type="ANY",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=1),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                )
            ],
        ),
    )

    normalized = normalize_cohort(expression)
    assert normalized.additional_criteria is not None
    assert normalized.additional_criteria.mode == "ANY"
    assert len(normalized.additional_criteria.criteria) == 1


def test_normalize_cohort_inclusion_rules():
    expression = CohortExpression(
        concept_sets=[_concept_set(1, include=111, exclude=999)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
        inclusion_rules=[
            InclusionRule(
                name="rule-1",
                expression=CriteriaGroup(
                    type="ALL",
                    criteria_list=[
                        CorelatedCriteria(
                            criteria=ConditionOccurrence(codeset_id=1),
                            occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                        )
                    ],
                ),
            )
        ],
    )

    normalized = normalize_cohort(expression)
    assert len(normalized.inclusion_rules) == 1
    assert normalized.inclusion_rules[0].name == "rule-1"
    assert normalized.inclusion_rules[0].expression is not None


def test_normalize_new_domains():
    cases = [
        (Measurement(codeset_id=1), "measurement"),
        (ProcedureOccurrence(codeset_id=1), "procedure_occurrence"),
        (Observation(codeset_id=1), "observation"),
        (VisitDetail(codeset_id=1), "visit_detail"),
        (DeviceExposure(codeset_id=1), "device_exposure"),
        (Specimen(codeset_id=1), "specimen"),
        (Death(codeset_id=1), "death"),
        (ObservationPeriod(), "observation_period"),
        (PayerPlanPeriod(), "payer_plan_period"),
        (ConditionEra(codeset_id=1), "condition_era"),
        (DrugEra(codeset_id=1), "drug_era"),
        (DoseEra(codeset_id=1), "dose_era"),
        (LocationRegion(codeset_id=1), "location_history"),
    ]
    for criteria, expected_table in cases:
        normalized = normalize_criterion(criteria)
        assert normalized.source_table == expected_table
