from __future__ import annotations

from typing import Callable, Dict, Type

from ...cohortdefinition.criteria import (
    ConditionOccurrence,
    ConditionEra,
    Criteria,
    Death,
    DeviceExposure,
    DoseEra,
    DrugExposure,
    DrugEra,
    LocationRegion,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)
from .condition_era import lower_condition_era
from ..errors import UnsupportedCriterionError
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .condition_occurrence import lower_condition_occurrence
from .death import lower_death
from .device_exposure import lower_device_exposure
from .dose_era import lower_dose_era
from .drug_exposure import lower_drug_exposure
from .drug_era import lower_drug_era
from .measurement import lower_measurement
from .location_region import lower_location_region
from .observation import lower_observation
from .observation_period import lower_observation_period
from .payer_plan_period import lower_payer_plan_period
from .procedure_occurrence import lower_procedure_occurrence
from .specimen import lower_specimen
from .visit_detail import lower_visit_detail
from .visit_occurrence import lower_visit_occurrence

LowerFn = Callable[[NormalizedCriterion], EventPlan]


LOWERERS: Dict[Type[Criteria], LowerFn] = {
    ConditionOccurrence: lower_condition_occurrence,
    DrugExposure: lower_drug_exposure,
    VisitOccurrence: lower_visit_occurrence,
    Measurement: lower_measurement,
    ProcedureOccurrence: lower_procedure_occurrence,
    Observation: lower_observation,
    VisitDetail: lower_visit_detail,
    DeviceExposure: lower_device_exposure,
    Specimen: lower_specimen,
    Death: lower_death,
    ObservationPeriod: lower_observation_period,
    PayerPlanPeriod: lower_payer_plan_period,
    ConditionEra: lower_condition_era,
    DrugEra: lower_drug_era,
    DoseEra: lower_dose_era,
    LocationRegion: lower_location_region,
}


def lower_criterion(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    lowerer = LOWERERS.get(type(criterion.raw_criteria))
    if lowerer is not None:
        return lowerer(criterion, criterion_index=criterion_index)
    raise UnsupportedCriterionError(
        f"No lowerer available for {criterion.criterion_type}."
    )
