from __future__ import annotations

from ...cohortdefinition.criteria import PayerPlanPeriod
from ..build_context import BuildContext
from .common import (
    apply_codeset_filter,
    apply_date_range,
    apply_first_event,
    apply_interval_range,
    apply_user_defined_period,
)
from .patterns import (
    apply_age_and_gender_filters,
    apply_age_at_start_end_filters,
    finalize_criteria_events,
)
from .registry import register


@register("PayerPlanPeriod")
def build_payer_plan_period(criteria: PayerPlanPeriod, ctx: BuildContext):
    table = ctx.table("payer_plan_period")

    table = apply_date_range(
        table, "payer_plan_period_start_date", criteria.period_start_date
    )
    table = apply_date_range(
        table, "payer_plan_period_end_date", criteria.period_end_date
    )

    table = apply_interval_range(
        table,
        "payer_plan_period_start_date",
        "payer_plan_period_end_date",
        criteria.period_length,
    )

    table = apply_age_at_start_end_filters(
        table,
        ctx=ctx,
        start_column="payer_plan_period_start_date",
        end_column="payer_plan_period_end_date",
        age_at_start=criteria.age_at_start,
        age_at_end=criteria.age_at_end,
    )
    table = apply_age_and_gender_filters(
        table,
        ctx=ctx,
        age_column="payer_plan_period_start_date",
        age_range=None,
        genders=criteria.gender,
        gender_selection=criteria.gender_cs,
    )

    table = apply_codeset_filter(table, "payer_concept_id", criteria.payer_concept, ctx)
    table = apply_codeset_filter(table, "plan_concept_id", criteria.plan_concept, ctx)
    table = apply_codeset_filter(
        table, "sponsor_concept_id", criteria.sponsor_concept, ctx
    )
    table = apply_codeset_filter(
        table, "stop_reason_concept_id", criteria.stop_reason_concept, ctx
    )
    table = apply_codeset_filter(
        table, "payer_source_concept_id", criteria.payer_source_concept, ctx
    )
    table = apply_codeset_filter(
        table, "plan_source_concept_id", criteria.plan_source_concept, ctx
    )
    table = apply_codeset_filter(
        table, "sponsor_source_concept_id", criteria.sponsor_source_concept, ctx
    )
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

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key="payer_plan_period_id",
        start_column=start_column,
        end_column=end_column,
    )
    return events
