from __future__ import annotations

from circe.cohortdefinition.criteria import DrugEra
from circe.extensions import lowerer

from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from ..plan.schema import GAP_DAYS, OCCURRENCE_COUNT
from .common import (
    append_duration_filter,
    append_numeric_filter,
    build_standard_domain_plan,
    lower_common_steps,
)


@lowerer(DrugEra)
def lower_drug_era(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    steps = lower_common_steps(criterion)
    post_standardize_steps = []
    raw = criterion.raw_criteria

    append_numeric_filter(
        post_standardize_steps,
        column=OCCURRENCE_COUNT,
        value=raw.occurrence_count,
    )
    append_numeric_filter(
        post_standardize_steps,
        column=GAP_DAYS,
        value=raw.gap_days,
    )
    append_duration_filter(post_standardize_steps, value=raw.era_length)

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
        post_standardize_steps=post_standardize_steps,
    )
