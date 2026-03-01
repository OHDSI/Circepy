from __future__ import annotations

import pytest

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
from circe.cohortdefinition.core import ConceptSetSelection, NumericRange
from circe.execution.normalize.cohort import normalize_cohort
from circe.execution.errors import UnsupportedFeatureError
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
    assert 1 in normalized.concept_sets
    assert tuple(item.concept_id for item in normalized.concept_sets[1].items) == (
        111,
        999,
    )
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


def test_normalize_cohort_preserves_concept_set_item_expansion_flags():
    expression = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    items=[
                        ConceptSetItem(
                            concept=Concept(conceptId=111),
                            includeDescendants=True,
                        )
                    ]
                ),
            )
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
    )

    normalized = normalize_cohort(expression)
    assert normalized.concept_sets[1].items[0].include_descendants is True


def test_normalize_cohort_preserves_expression_level_concept_set_flags():
    expression = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    concept=Concept(conceptId=111),
                    includeMapped=True,
                ),
            )
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)]
        ),
    )

    normalized = normalize_cohort(expression)
    normalized_item = normalized.concept_sets[1].items[0]
    assert normalized_item.concept_id == 111
    assert normalized_item.include_mapped is True
    assert normalized_item.is_excluded is False


def test_normalize_criterion_rejects_criterion_local_correlated_criteria():
    criteria = ConditionOccurrence(
        codeset_id=1,
        correlated_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=1),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                )
            ],
        ),
    )

    with pytest.raises(
        UnsupportedFeatureError,
        match="criterion.correlated_criteria is not implemented",
    ):
        _ = normalize_criterion(criteria)


def test_normalize_criterion_includes_race_and_ethnicity_person_filters():
    criteria = ConditionOccurrence(codeset_id=1)
    criteria.__dict__["race"] = [Concept(conceptId=8527)]
    criteria.__dict__["race_cs"] = ConceptSetSelection(codeset_id=2, is_exclusion=False)
    criteria.__dict__["ethnicity"] = [Concept(conceptId=38003564)]
    criteria.__dict__["ethnicity_cs"] = ConceptSetSelection(
        codeset_id=3,
        is_exclusion=False,
    )

    normalized = normalize_criterion(criteria)
    assert normalized.person_filters.race_concept_ids == (8527,)
    assert normalized.person_filters.race_codeset_id == 2
    assert normalized.person_filters.ethnicity_concept_ids == (38003564,)
    assert normalized.person_filters.ethnicity_codeset_id == 3
