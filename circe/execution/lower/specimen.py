from __future__ import annotations

from circe.extensions import lowerer

from ...cohortdefinition.criteria import Specimen
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import (
    append_concept_filters,
    append_numeric_filter,
    append_text_filter,
    build_standard_domain_plan,
    lower_common_steps,
)


@lowerer(Specimen)
def lower_specimen(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, Specimen):
        raise TypeError("lower_specimen requires Specimen criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="specimen_type_concept_id",
        concepts=raw.specimen_type,
        codeset_selection=raw.specimen_type_cs,
        exclude=bool(raw.specimen_type_exclude),
    )
    append_numeric_filter(steps, column="quantity", value=raw.quantity)
    append_concept_filters(
        steps,
        column="unit_concept_id",
        concepts=raw.unit,
        codeset_selection=raw.unit_cs,
    )
    append_concept_filters(
        steps,
        column="anatomic_site_concept_id",
        concepts=raw.anatomic_site,
        codeset_selection=raw.anatomic_site_cs,
    )
    append_concept_filters(
        steps,
        column="disease_status_concept_id",
        concepts=raw.disease_status,
        codeset_selection=raw.disease_status_cs,
    )
    append_text_filter(steps, column="specimen_source_id", value=raw.source_id)

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
