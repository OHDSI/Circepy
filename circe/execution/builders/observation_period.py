from __future__ import annotations

from ...cohortdefinition.criteria import ObservationPeriod
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_interval_range,
    apply_user_defined_period,
    standardize_output,
)
from .groups import apply_criteria_group
from ...extensions import register_ibis_builder


@register_ibis_builder("ObservationPeriod")
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

    if criteria.age_at_start:
        table = apply_age_filter(
            table, criteria.age_at_start, ctx, "observation_period_start_date"
        )
    if criteria.age_at_end:
        table = apply_age_filter(
            table, criteria.age_at_end, ctx, "observation_period_end_date"
        )

    table, start_column, end_column = apply_user_defined_period(
        table,
        "observation_period_start_date",
        "observation_period_end_date",
        criteria.user_defined_period,
    )

    if criteria.first:
        table = apply_first_event(table, start_column, "observation_period_id")

    events = standardize_output(
        table,
        primary_key="observation_period_id",
        start_column=start_column,
        end_column=end_column,
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
