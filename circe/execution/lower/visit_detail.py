from __future__ import annotations

from ...cohortdefinition.criteria import VisitDetail
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import append_concept_filters, build_standard_domain_plan, lower_common_steps


def lower_visit_detail(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, VisitDetail):
        raise TypeError("lower_visit_detail requires VisitDetail criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="visit_detail_type_concept_id",
        concepts=raw.visit_detail_type,
        codeset_selection=raw.visit_detail_type_cs,
        exclude=bool(raw.visit_detail_type_exclude),
    )
    append_concept_filters(
        steps,
        column="discharge_to_concept_id",
        concepts=raw.discharge_to,
        codeset_selection=raw.discharge_to_cs,
    )

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
