from __future__ import annotations

from ...cohortdefinition.criteria import DoseEra
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_gender_filter,
    apply_interval_range,
    apply_numeric_range,
    standardize_output,
)
from .groups import apply_criteria_group
from ...extensions import register_ibis_builder


@register_ibis_builder("DoseEra")
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

    if criteria.age_at_start:
        table = apply_age_filter(
            table, criteria.age_at_start, ctx, "dose_era_start_date"
        )
    if criteria.age_at_end:
        table = apply_age_filter(table, criteria.age_at_end, ctx, "dose_era_end_date")
    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)

    if criteria.first:
        table = apply_first_event(table, "dose_era_start_date", "dose_era_id")

    events = standardize_output(
        table,
        primary_key="dose_era_id",
        start_column="dose_era_start_date",
        end_column="dose_era_end_date",
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
