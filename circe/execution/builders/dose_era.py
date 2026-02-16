from __future__ import annotations

from ...cohortdefinition.criteria import DoseEra
from ..build_context import BuildContext
from .common import (
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_interval_range,
    apply_numeric_range,
)
from .patterns import (
    apply_age_and_gender_filters,
    apply_age_at_start_end_filters,
    finalize_criteria_events,
)
from .registry import register


@register("DoseEra")
def build_dose_era(criteria: DoseEra, ctx: BuildContext):
    table = ctx.table("dose_era")

    table = apply_codeset_filter(table, "drug_concept_id", criteria.codeset_id, ctx)
    table = apply_date_range(table, "dose_era_start_date", criteria.era_start_date)
    table = apply_date_range(table, "dose_era_end_date", criteria.era_end_date)

    table = apply_concept_criteria(
        table,
        column="unit_concept_id",
        concepts=criteria.unit,
        selection=criteria.unit_cs,
        ctx=ctx,
    )

    table = apply_numeric_range(table, "dose_value", criteria.dose_value)
    table = apply_interval_range(
        table, "dose_era_start_date", "dose_era_end_date", criteria.era_length
    )

    table = apply_age_at_start_end_filters(
        table,
        ctx=ctx,
        start_column="dose_era_start_date",
        end_column="dose_era_end_date",
        age_at_start=criteria.age_at_start,
        age_at_end=criteria.age_at_end,
    )
    table = apply_age_and_gender_filters(
        table,
        ctx=ctx,
        age_column="dose_era_start_date",
        age_range=None,
        genders=criteria.gender,
        gender_selection=criteria.gender_cs,
    )

    if criteria.first:
        table = apply_first_event(table, "dose_era_start_date", "dose_era_id")

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key="dose_era_id",
        start_column="dose_era_start_date",
        end_column="dose_era_end_date",
    )
    return events
