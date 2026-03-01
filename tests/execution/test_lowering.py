from __future__ import annotations

import pytest

from circe.cohortdefinition import (
    ConditionEra,
    ConditionOccurrence,
    Death,
    DeviceExposure,
    DoseEra,
    Measurement,
    LocationRegion,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    DrugEra,
    VisitDetail,
)
from circe.execution.lower.criteria import lower_criterion
from circe.execution.normalize.criteria import normalize_criterion
from circe.execution.plan.events import (
    FilterByCodeset,
    FilterByConceptSet,
    FilterByNumericRange,
    FilterByPersonEthnicity,
    FilterByPersonRace,
    KeepFirstPerPerson,
    FilterByText,
    StandardizeEventShape,
)
from circe.vocabulary import Concept


def test_lowering_condition_occurrence_emits_expected_steps():
    normalized = normalize_criterion(
        ConditionOccurrence(
            codeset_id=1,
            first=True,
        )
    )

    plan = lower_criterion(normalized, criterion_index=3)

    assert plan.source.table_name == "condition_occurrence"
    assert plan.source.concept_column == "condition_concept_id"
    assert any(isinstance(step, FilterByCodeset) for step in plan.steps)
    assert any(isinstance(step, KeepFirstPerPerson) for step in plan.steps)
    standardize = [
        step for step in plan.steps if isinstance(step, StandardizeEventShape)
    ]
    assert len(standardize) == 1
    assert standardize[0].criterion_index == 3


def test_lowering_measurement_emits_domain_specific_filter_steps():
    normalized = normalize_criterion(
        Measurement(
            codeset_id=1,
            value_as_number={"op": "gte", "value": 10},
            unit=[{"conceptId": 9002}],
            value_as_concept=[{"conceptId": 7002}],
        )
    )

    plan = lower_criterion(normalized, criterion_index=5)

    assert any(isinstance(step, FilterByNumericRange) for step in plan.steps)
    # unit + value_as_concept should emit concept filters in addition to codeset filter
    concept_steps = [step for step in plan.steps if isinstance(step, FilterByConceptSet)]
    assert len(concept_steps) >= 2


def test_lowering_observation_procedure_visit_detail_emit_domain_filters():
    observation_plan = lower_criterion(
        normalize_criterion(
            Observation(
                codeset_id=1,
                observation_type=[Concept(conceptId=1001)],
                value_as_number={"op": "gte", "value": 2},
                value_as_string={"op": "contains", "text": "abc"},
            )
        ),
        criterion_index=6,
    )
    assert any(isinstance(step, FilterByConceptSet) for step in observation_plan.steps)
    assert any(isinstance(step, FilterByNumericRange) for step in observation_plan.steps)
    assert any(isinstance(step, FilterByText) for step in observation_plan.steps)

    procedure_plan = lower_criterion(
        normalize_criterion(
            ProcedureOccurrence(
                codeset_id=1,
                procedure_type=[Concept(conceptId=2001)],
                quantity={"op": "gte", "value": 1},
            )
        ),
        criterion_index=7,
    )
    assert any(isinstance(step, FilterByConceptSet) for step in procedure_plan.steps)
    assert any(isinstance(step, FilterByNumericRange) for step in procedure_plan.steps)

    visit_detail_plan = lower_criterion(
        normalize_criterion(
            VisitDetail(
                codeset_id=1,
                visit_detail_type=[Concept(conceptId=3001)],
                discharge_to=[Concept(conceptId=3002)],
            )
        ),
        criterion_index=8,
    )
    concept_steps = [s for s in visit_detail_plan.steps if isinstance(s, FilterByConceptSet)]
    assert len(concept_steps) >= 2


@pytest.mark.parametrize(
    ("criteria", "table_name", "concept_column", "expects_codeset_step"),
    [
        (Measurement(codeset_id=1), "measurement", "measurement_concept_id", True),
        (
            ProcedureOccurrence(codeset_id=1),
            "procedure_occurrence",
            "procedure_concept_id",
            True,
        ),
        (Observation(codeset_id=1), "observation", "observation_concept_id", True),
        (VisitDetail(codeset_id=1), "visit_detail", "visit_detail_concept_id", True),
        (DeviceExposure(codeset_id=1), "device_exposure", "device_concept_id", True),
        (Specimen(codeset_id=1), "specimen", "specimen_concept_id", True),
        (Death(codeset_id=1), "death", "cause_concept_id", True),
        (ObservationPeriod(), "observation_period", "period_type_concept_id", False),
        (PayerPlanPeriod(), "payer_plan_period", "payer_concept_id", False),
        (ConditionEra(codeset_id=1), "condition_era", "condition_concept_id", True),
        (DrugEra(codeset_id=1), "drug_era", "drug_concept_id", True),
        (DoseEra(codeset_id=1), "dose_era", "drug_concept_id", True),
        (LocationRegion(codeset_id=1), "location_history", "region_concept_id", True),
    ],
)
def test_lowering_new_domains_emit_standardized_plans(
    criteria,
    table_name,
    concept_column,
    expects_codeset_step,
):
    normalized = normalize_criterion(criteria)
    plan = lower_criterion(normalized, criterion_index=4)

    assert plan.source.table_name == table_name
    assert plan.source.concept_column == concept_column
    assert any(isinstance(step, FilterByCodeset) for step in plan.steps) is expects_codeset_step
    standardize = [
        step for step in plan.steps if isinstance(step, StandardizeEventShape)
    ]
    assert len(standardize) == 1


def test_lowering_emits_race_and_ethnicity_person_filters():
    criteria = ConditionOccurrence(codeset_id=1)
    criteria.__dict__["race"] = [Concept(conceptId=8527)]
    criteria.__dict__["ethnicity"] = [Concept(conceptId=38003564)]

    plan = lower_criterion(normalize_criterion(criteria), criterion_index=9)
    assert any(isinstance(step, FilterByPersonRace) for step in plan.steps)
    assert any(isinstance(step, FilterByPersonEthnicity) for step in plan.steps)
