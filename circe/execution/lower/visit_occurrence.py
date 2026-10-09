from __future__ import annotations

from circe.extensions import lowerer

from ...cohortdefinition.criteria import VisitOccurrence
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan, PlanStep
from .common import (
    append_care_site_filters,
    append_care_site_location_region_filter,
    append_concept_filters,
    append_duration_filter,
    append_provider_specialty_filters,
    build_standard_domain_plan,
    lower_common_steps,
)


@lowerer(VisitOccurrence)
def lower_visit_occurrence(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, VisitOccurrence):
        raise TypeError("lower_visit_occurrence requires VisitOccurrence criteria")

    steps = lower_common_steps(criterion)
    post_standardize_steps: list[PlanStep] = []

    append_concept_filters(
        steps,
        column="visit_type_concept_id",
        concepts=raw.visit_type,
        codeset_selection=raw.visit_type_cs,
        exclude=bool(raw.visit_type_exclude),
    )
    append_provider_specialty_filters(
        steps,
        concepts=raw.provider_specialty,
        codeset_selection=raw.provider_specialty_cs,
    )
    append_care_site_filters(
        steps,
        concepts=raw.place_of_service,
        codeset_selection=raw.place_of_service_cs,
    )
    append_care_site_location_region_filter(
        steps,
        start_date_column=criterion.start_date_column,
        end_date_column=criterion.end_date_column,
        codeset_id=raw.place_of_service_location,
    )
    append_duration_filter(post_standardize_steps, value=raw.visit_length)

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
        post_standardize_steps=post_standardize_steps,
    )
