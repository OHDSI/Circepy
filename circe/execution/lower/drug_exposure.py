from __future__ import annotations

from ...cohortdefinition.criteria import DrugExposure
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


def lower_drug_exposure(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, DrugExposure):
        raise TypeError("lower_drug_exposure requires DrugExposure criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="drug_type_concept_id",
        concepts=raw.drug_type,
        codeset_selection=raw.drug_type_cs,
        exclude=bool(raw.drug_type_exclude),
    )
    append_text_filter(steps, column="stop_reason", value=raw.stop_reason)
    append_concept_filters(
        steps,
        column="route_concept_id",
        concepts=raw.route_concept,
        codeset_selection=raw.route_concept_cs,
    )
    append_concept_filters(
        steps,
        column="dose_unit_concept_id",
        concepts=raw.dose_unit,
        codeset_selection=raw.dose_unit_cs,
    )
    append_text_filter(steps, column="lot_number", value=raw.lot_number)
    append_numeric_filter(steps, column="refills", value=raw.refills)
    append_numeric_filter(steps, column="quantity", value=raw.quantity)
    append_numeric_filter(steps, column="days_supply", value=raw.days_supply)
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
