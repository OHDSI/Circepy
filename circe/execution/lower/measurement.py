from __future__ import annotations

from ...cohortdefinition.criteria import Measurement
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


def lower_measurement(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, Measurement):
        raise TypeError("lower_measurement requires Measurement criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="measurement_type_concept_id",
        concepts=raw.measurement_type,
        codeset_selection=raw.measurement_type_cs,
        exclude=bool(raw.measurement_type_exclude),
    )
    append_concept_filters(
        steps,
        column="operator_concept_id",
        concepts=raw.operator,
        codeset_selection=raw.operator_cs,
    )
    append_numeric_filter(steps, column="value_as_number", value=raw.value_as_number)
    append_text_filter(steps, column="value_as_string", value=raw.value_as_string)
    append_concept_filters(
        steps,
        column="value_as_concept_id",
        concepts=raw.value_as_concept,
        codeset_selection=raw.value_as_concept_cs,
    )
    append_concept_filters(
        steps,
        column="unit_concept_id",
        concepts=raw.unit,
        codeset_selection=raw.unit_cs,
    )
    append_numeric_filter(steps, column="range_low", value=raw.range_low)
    append_numeric_filter(steps, column="range_high", value=raw.range_high)
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
