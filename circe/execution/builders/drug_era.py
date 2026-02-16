from __future__ import annotations

from ...cohortdefinition.criteria import DrugEra
from ..build_context import BuildContext
from .common import (
    apply_codeset_filter,
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


@register("DrugEra")
def build_drug_era(criteria: DrugEra, ctx: BuildContext):
    table = ctx.table("drug_era")

    table = apply_codeset_filter(table, "drug_concept_id", criteria.codeset_id, ctx)
    table = apply_date_range(table, "drug_era_start_date", criteria.era_start_date)
    table = apply_date_range(table, "drug_era_end_date", criteria.era_end_date)
    table = apply_numeric_range(table, "drug_exposure_count", criteria.occurrence_count)
    table = apply_numeric_range(table, "gap_days", criteria.gap_days)
    table = apply_interval_range(
        table, "drug_era_start_date", "drug_era_end_date", criteria.era_length
    )

    table = apply_age_at_start_end_filters(
        table,
        ctx=ctx,
        start_column="drug_era_start_date",
        end_column="drug_era_end_date",
        age_at_start=criteria.age_at_start,
        age_at_end=criteria.age_at_end,
    )
    table = apply_age_and_gender_filters(
        table,
        ctx=ctx,
        age_column="drug_era_start_date",
        age_range=None,
        genders=criteria.gender,
        gender_selection=criteria.gender_cs,
    )

    if criteria.first:
        table = apply_first_event(table, "drug_era_start_date", "drug_era_id")

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key="drug_era_id",
        start_column="drug_era_start_date",
        end_column="drug_era_end_date",
    )
    return events
