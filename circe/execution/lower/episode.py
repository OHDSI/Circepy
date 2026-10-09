from __future__ import annotations

from circe.cohortdefinition.criteria import Episode
from circe.extensions import lowerer

from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import (
    append_concept_filters,
    append_numeric_filter,
    build_standard_domain_plan,
    lower_common_steps,
)


@lowerer(Episode)
def lower_episode(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    steps = lower_common_steps(criterion)
    raw = criterion.raw_criteria

    append_numeric_filter(steps, column="episode_number", value=raw.episode_number)
    append_concept_filters(
        steps,
        column="episode_object_concept_id",
        codeset_selection=raw.episode_object_concept_cs,
    )
    append_concept_filters(
        steps,
        column="episode_type_concept_id",
        codeset_selection=raw.episode_type_cs,
    )

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
