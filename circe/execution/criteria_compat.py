from __future__ import annotations

from enum import IntEnum
from typing import Any

from ..cohortdefinition.criteria import (
    ConditionEra,
    ConditionOccurrence,
    CorelatedCriteria,
    Criteria,
    Death,
    DemographicCriteria,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)

CorrelatedCriteria = CorelatedCriteria
DemoGraphicCriteria = DemographicCriteria


class OccurrenceType(IntEnum):
    EXACTLY = 0
    AT_MOST = 1
    AT_LEAST = 2


_CONCEPT_ID_OVERRIDES: dict[str, str] = {
    "Death": "cause_concept_id",
    "DoseEra": "drug_concept_id",
    "VisitDetail": "visit_detail_concept_id",
}

_PRIMARY_KEY_OVERRIDES: dict[str, str] = {
    "Death": "person_id",
}

_START_DATE_OVERRIDES: dict[str, str] = {
    "ConditionEra": "condition_era_start_date",
    "DrugExposure": "drug_exposure_start_date",
    "Measurement": "measurement_date",
    "Observation": "observation_date",
    "DeviceExposure": "device_exposure_start_date",
    "ProcedureOccurrence": "procedure_date",
    "DrugEra": "drug_era_start_date",
    "DoseEra": "dose_era_start_date",
    "ObservationPeriod": "observation_period_start_date",
    "Specimen": "specimen_date",
    "Death": "death_date",
    "VisitDetail": "visit_detail_start_date",
    "PayerPlanPeriod": "payer_plan_period_start_date",
}

_END_DATE_OVERRIDES: dict[str, str] = {
    "ConditionEra": "condition_era_end_date",
    "DrugExposure": "drug_exposure_end_date",
    "Measurement": "measurement_date",
    "Observation": "observation_date",
    "DeviceExposure": "device_exposure_end_date",
    "ProcedureOccurrence": "procedure_date",
    "DrugEra": "drug_era_end_date",
    "DoseEra": "dose_era_end_date",
    "ObservationPeriod": "observation_period_end_date",
    "Specimen": "specimen_date",
    "Death": "death_date",
    "VisitDetail": "visit_detail_end_date",
    "PayerPlanPeriod": "payer_plan_period_end_date",
}


def _to_snake_case(name: str) -> str:
    output: list[str] = []
    for idx, char in enumerate(name):
        if char.isupper() and idx > 0:
            output.append("_")
        output.append(char.lower())
    return "".join(output)


def _snake_case_class_name(cls: type[Criteria]) -> str:
    return _to_snake_case(cls.__name__)


def _get_concept_id_column(self: Criteria) -> str:
    cls_name = self.__class__.__name__
    overridden = _CONCEPT_ID_OVERRIDES.get(cls_name)
    if overridden:
        return overridden
    table_name = self.snake_case_class_name()
    return f"{table_name.split('_')[0]}_concept_id"


def _get_primary_key_column(self: Criteria) -> str:
    cls_name = self.__class__.__name__
    overridden = _PRIMARY_KEY_OVERRIDES.get(cls_name)
    if overridden:
        return overridden
    return f"{self.snake_case_class_name()}_id"


def _get_start_date_column(self: Criteria) -> str:
    cls_name = self.__class__.__name__
    overridden = _START_DATE_OVERRIDES.get(cls_name)
    if overridden:
        return overridden
    return f"{self.snake_case_class_name().split('_')[0]}_start_date"


def _get_end_date_column(self: Criteria) -> str:
    cls_name = self.__class__.__name__
    overridden = _END_DATE_OVERRIDES.get(cls_name)
    if overridden:
        return overridden
    return f"{self.snake_case_class_name().split('_')[0]}_end_date"


def ensure_criteria_compat() -> None:
    if getattr(Criteria, "_execution_compat_patched", False):
        return

    Criteria.snake_case_class_name = classmethod(_snake_case_class_name)
    Criteria.get_concept_id_column = _get_concept_id_column
    Criteria.get_primary_key_column = _get_primary_key_column
    Criteria.get_start_date_column = _get_start_date_column
    Criteria.get_end_date_column = _get_end_date_column
    Criteria._execution_compat_patched = True


CRITERIA_TYPE_MAP: dict[str, type[Criteria]] = {
    "ConditionOccurrence": ConditionOccurrence,
    "ConditionEra": ConditionEra,
    "VisitOccurrence": VisitOccurrence,
    "DrugExposure": DrugExposure,
    "DrugEra": DrugEra,
    "DoseEra": DoseEra,
    "ObservationPeriod": ObservationPeriod,
    "Measurement": Measurement,
    "Observation": Observation,
    "Specimen": Specimen,
    "DeviceExposure": DeviceExposure,
    "ProcedureOccurrence": ProcedureOccurrence,
    "Death": Death,
    "VisitDetail": VisitDetail,
    "PayerPlanPeriod": PayerPlanPeriod,
}
CRITERIA_TYPE_MAP_CASEFOLD: dict[str, type[Criteria]] = {
    name.casefold(): model for name, model in CRITERIA_TYPE_MAP.items()
}


def parse_single_criteria(criteria_dict: Any) -> Criteria:
    if isinstance(criteria_dict, Criteria):
        return criteria_dict

    if not isinstance(criteria_dict, dict):
        raise ValueError("Criteria wrapper must be an object.")

    if len(criteria_dict) != 1:
        raise ValueError("Criteria wrapper must contain exactly one criteria type key.")

    criteria_type, criteria_data = next(iter(criteria_dict.items()))
    model_cls = CRITERIA_TYPE_MAP.get(criteria_type)
    if model_cls is None and isinstance(criteria_type, str):
        model_cls = CRITERIA_TYPE_MAP_CASEFOLD.get(criteria_type.casefold())
    if model_cls is None:
        raise ValueError(f"Unsupported criteria type: {criteria_type}")

    if criteria_data is None:
        criteria_data = {}

    if not isinstance(criteria_data, dict):
        raise ValueError(f"Criteria payload for {criteria_type} must be an object.")

    return model_cls.model_validate(criteria_data, strict=False)


def parse_criteria_list(criteria_list_data: Any) -> list[Criteria]:
    if criteria_list_data is None:
        return []

    if not isinstance(criteria_list_data, list):
        raise ValueError("Criteria list must be a list.")

    criteria_instances: list[Criteria] = []
    for idx, criteria_dict in enumerate(criteria_list_data):
        try:
            parsed = parse_single_criteria(criteria_dict)
        except ValueError as exc:
            raise ValueError(f"Invalid criteria wrapper at index {idx}: {exc}") from exc
        criteria_instances.append(parsed)
    return criteria_instances


ensure_criteria_compat()
