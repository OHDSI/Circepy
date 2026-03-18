from __future__ import annotations

from ...cohortdefinition.criteria import PayerPlanPeriod
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_date_range,
    apply_first_event,
    apply_gender_filter,
    apply_interval_range,
    apply_user_defined_period,
    standardize_output,
)
from .groups import apply_criteria_group
from .registry import register


@register("PayerPlanPeriod")
def build_payer_plan_period(criteria: PayerPlanPeriod, ctx: BuildContext):
    table = ctx.table("payer_plan_period")

    table = apply_date_range(table, "payer_plan_period_start_date", criteria.period_start_date)
    table = apply_date_range(table, "payer_plan_period_end_date", criteria.period_end_date)

    table = apply_interval_range(
        table,
        "payer_plan_period_start_date",
        "payer_plan_period_end_date",
        criteria.period_length,
    )

    if criteria.age_at_start:
        table = apply_age_filter(table, criteria.age_at_start, ctx, "payer_plan_period_start_date")
    if criteria.age_at_end:
        table = apply_age_filter(table, criteria.age_at_end, ctx, "payer_plan_period_end_date")

    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)

    table = apply_codeset_filter(table, "payer_concept_id", criteria.payer_concept, ctx)
    table = apply_codeset_filter(table, "plan_concept_id", criteria.plan_concept, ctx)
    table = apply_codeset_filter(table, "sponsor_concept_id", criteria.sponsor_concept, ctx)
    table = apply_codeset_filter(table, "stop_reason_concept_id", criteria.stop_reason_concept, ctx)
    table = apply_codeset_filter(table, "payer_source_concept_id", criteria.payer_source_concept, ctx)
    table = apply_codeset_filter(table, "plan_source_concept_id", criteria.plan_source_concept, ctx)
    table = apply_codeset_filter(table, "sponsor_source_concept_id", criteria.sponsor_source_concept, ctx)
    table = apply_codeset_filter(
        table, "stop_reason_source_concept_id", criteria.stop_reason_source_concept, ctx
    )

    table, start_column, end_column = apply_user_defined_period(
        table,
        "payer_plan_period_start_date",
        "payer_plan_period_end_date",
        criteria.user_defined_period,
    )

    if criteria.first:
        table = apply_first_event(table, start_column, "payer_plan_period_id")

    events = standardize_output(
        table,
        primary_key="payer_plan_period_id",
        start_column=start_column,
        end_column=end_column,
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
