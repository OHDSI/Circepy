from __future__ import annotations

from ...cohortdefinition.criteria import ObservationPeriod
from ..build_context import BuildContext
from .common import (
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_interval_range,
    apply_user_defined_period,
)
from .patterns import (
    apply_age_at_start_end_filters,
    finalize_criteria_events,
)
from .registry import register


@register("ObservationPeriod")
def build_observation_period(criteria: ObservationPeriod, ctx: BuildContext):
    table = ctx.table("observation_period")

    table = apply_date_range(
        table, "observation_period_start_date", criteria.period_start_date
    )
    table = apply_date_range(
        table, "observation_period_end_date", criteria.period_end_date
    )

    table = apply_concept_criteria(
        table,
        column="period_type_concept_id",
        concepts=criteria.period_type,
        selection=criteria.period_type_cs,
        ctx=ctx,
    )

    table = apply_interval_range(
        table,
        "observation_period_start_date",
        "observation_period_end_date",
        criteria.period_length,
    )

    table = apply_age_at_start_end_filters(
        table,
        ctx=ctx,
        start_column="observation_period_start_date",
        end_column="observation_period_end_date",
        age_at_start=criteria.age_at_start,
        age_at_end=criteria.age_at_end,
    )

    table, start_column, end_column = apply_user_defined_period(
        table,
        "observation_period_start_date",
        "observation_period_end_date",
        criteria.user_defined_period,
    )

    if criteria.first:
        table = apply_first_event(table, start_column, "observation_period_id")

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key="observation_period_id",
        start_column=start_column,
        end_column=end_column,
    )
    return events
