from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Literal

from ...execution._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class SubsetOperator:
    """Marker base class for subset operators."""


@frozen_slots_dataclass
class DemographicSubsetOperator(SubsetOperator):
    age_range: tuple[int | None, int | None] | None = None
    gender_concept_ids: tuple[int, ...] = ()
    race_concept_ids: tuple[int, ...] = ()
    ethnicity_concept_ids: tuple[int, ...] = ()


@frozen_slots_dataclass
class LimitSubsetOperator(SubsetOperator):
    first_only: bool = False
    last_only: bool = False
    min_prior_observation_days: int | None = None
    min_cohort_duration_days: int | None = None
    calendar_start_date: date | None = None
    calendar_end_date: date | None = None


@frozen_slots_dataclass
class CohortSubsetOperator(SubsetOperator):
    subset_cohort_id: int
    relationship: Literal["intersect", "exclude", "require_overlap"] = "intersect"
    target_anchor: Literal["start", "end"] = "start"
    subset_anchor: Literal["start", "end"] = "start"
    window_start_offset: int = 0
    window_end_offset: int = 0


SubsetOperatorType = (
    DemographicSubsetOperator
    | LimitSubsetOperator
    | CohortSubsetOperator
)


@frozen_slots_dataclass
class SubsetDefinition:
    subset_name: str
    parent_cohort_id: int
    operators: tuple[SubsetOperatorType, ...]
    subset_definition_id: str | None = None


def serialize_operator(operator: SubsetOperatorType) -> dict:
    payload = _json_ready(asdict(operator))
    payload["operator_type"] = operator.__class__.__name__
    return payload


def serialize_subset_definition(definition: SubsetDefinition) -> dict:
    return {
        "subset_name": definition.subset_name,
        "parent_cohort_id": int(definition.parent_cohort_id),
        "subset_definition_id": definition.subset_definition_id,
        "operators": [serialize_operator(op) for op in definition.operators],
    }


def _json_ready(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value
