from __future__ import annotations

from circe.cohortdefinition.criteria import DoseEra
from circe.extensions import lowerer

from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan, PlanStep
from .common import append_duration_filter, build_standard_domain_plan, lower_common_steps


@lowerer(DoseEra)
def lower_dose_era(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    steps = lower_common_steps(criterion)
    post_standardize_steps: list[PlanStep] = []
    append_duration_filter(post_standardize_steps, value=criterion.raw_criteria.era_length)

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
        post_standardize_steps=post_standardize_steps,
    )
