from __future__ import annotations

from circe.extensions import lowerer

from ...cohortdefinition.criteria import ConditionOccurrence
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import (
    append_concept_filters,
    append_provider_specialty_filters,
    append_text_filter,
    append_visit_filters,
    build_standard_domain_plan,
    lower_common_steps,
)


@lowerer(ConditionOccurrence)
def lower_condition_occurrence(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, ConditionOccurrence):
        raise TypeError("lower_condition_occurrence requires ConditionOccurrence criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="condition_type_concept_id",
        concepts=raw.condition_type,
        codeset_selection=raw.condition_type_cs,
        exclude=bool(raw.condition_type_exclude),
    )
    append_text_filter(steps, column="stop_reason", value=raw.stop_reason)
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
    append_concept_filters(
        steps,
        column="condition_status_concept_id",
        concepts=raw.condition_status,
        codeset_selection=raw.condition_status_cs,
    )

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
