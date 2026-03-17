from __future__ import annotations

from ...cohortdefinition.criteria import ConditionEra
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_date_range,
    apply_first_event,
    apply_gender_filter,
    apply_interval_range,
    apply_numeric_range,
    standardize_output,
)
from .groups import apply_criteria_group
from .registry import register


@register("ConditionEra")
def build_condition_era(criteria: ConditionEra, ctx: BuildContext):
    table = ctx.table("condition_era")

    table = apply_codeset_filter(table, "condition_concept_id", criteria.codeset_id, ctx)
    table = apply_date_range(table, "condition_era_start_date", criteria.era_start_date)
    table = apply_date_range(table, "condition_era_end_date", criteria.era_end_date)
    table = apply_numeric_range(table, "condition_occurrence_count", criteria.occurrence_count)
    table = apply_interval_range(
        table, "condition_era_start_date", "condition_era_end_date", criteria.era_length
    )

    if criteria.age_at_start:
        table = apply_age_filter(table, criteria.age_at_start, ctx, "condition_era_start_date")
    if criteria.age_at_end:
        table = apply_age_filter(table, criteria.age_at_end, ctx, "condition_era_end_date")

    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)

    if criteria.first:
        table = apply_first_event(table, "condition_era_start_date", "condition_era_id")

    events = standardize_output(
        table,
        primary_key="condition_era_id",
        start_column="condition_era_start_date",
        end_column="condition_era_end_date",
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
