from __future__ import annotations

from circe.extensions import lowerer

from ...cohortdefinition.criteria import Death
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import append_concept_filters, build_standard_domain_plan, lower_common_steps


@lowerer(Death)
def lower_death(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, Death):
        raise TypeError("lower_death requires Death criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="death_type_concept_id",
        concepts=raw.death_type,
        codeset_selection=raw.death_type_cs,
        exclude=bool(raw.death_type_exclude),
    )

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
