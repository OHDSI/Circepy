from __future__ import annotations

from circe.extensions import lowerer

from ...cohortdefinition.criteria import Observation
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


@lowerer(Observation)
def lower_observation(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, Observation):
        raise TypeError("lower_observation requires Observation criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="observation_type_concept_id",
        concepts=raw.observation_type,
        codeset_selection=raw.observation_type_cs,
        exclude=bool(raw.observation_type_exclude),
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
    append_concept_filters(
        steps,
        column="qualifier_concept_id",
        concepts=raw.qualifier,
        codeset_selection=raw.qualifier_cs,
    )
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
