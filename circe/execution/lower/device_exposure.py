from __future__ import annotations

from circe.extensions import lowerer

from ...cohortdefinition.criteria import DeviceExposure
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import (
    append_concept_filters,
    append_numeric_filter,
    append_provider_specialty_filters,
    append_text_filter,
    append_visit_filters,
    build_standard_domain_plan,
    lower_common_steps,
)


@lowerer(DeviceExposure)
def lower_device_exposure(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, DeviceExposure):
        raise TypeError("lower_device_exposure requires DeviceExposure criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="device_type_concept_id",
        concepts=raw.device_type,
        codeset_selection=raw.device_type_cs,
        exclude=bool(raw.device_type_exclude),
    )
    append_text_filter(steps, column="unique_device_id", value=raw.unique_device_id)
    append_numeric_filter(steps, column="quantity", value=raw.quantity)
    append_provider_specialty_filters(
        steps,
        concepts=raw.provider_specialty,
        codeset_selection=raw.provider_specialty_cs,
    )
    append_visit_filters(
        steps,
        visit_occurrence_column="visit_occurrence_id",
        concepts=raw.visit_type,
        codeset_selection=raw.visit_type_cs,
    )

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
