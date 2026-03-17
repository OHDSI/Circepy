from __future__ import annotations

from ...cohortdefinition.criteria import VisitDetail
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_care_site_filter,
    apply_codeset_filter,
    apply_concept_set_selection,
    apply_date_range,
    apply_first_event,
    apply_gender_filter,
    apply_interval_range,
    apply_location_region_filter,
    apply_provider_specialty_filter,
    project_event_columns,
    standardize_output,
)
from .groups import apply_criteria_group
from .registry import register


@register("VisitDetail")
def build_visit_detail(criteria: VisitDetail, ctx: BuildContext):
    table = ctx.table("visit_detail")

    table = apply_codeset_filter(table, "visit_detail_concept_id", criteria.codeset_id, ctx)
    if criteria.first:
        table = apply_first_event(table, "visit_detail_start_date", "visit_detail_id")
    table = apply_date_range(table, "visit_detail_start_date", criteria.visit_detail_start_date)
    table = apply_date_range(table, "visit_detail_end_date", criteria.visit_detail_end_date)
    table = apply_concept_set_selection(
        table, "visit_detail_type_concept_id", criteria.visit_detail_type_cs, ctx
    )
    if criteria.visit_detail_source_concept is not None:
        table = apply_codeset_filter(
            table,
            "visit_detail_source_concept_id",
            criteria.visit_detail_source_concept,
            ctx,
        )
    table = apply_interval_range(
        table,
        "visit_detail_start_date",
        "visit_detail_end_date",
        criteria.visit_detail_length,
    )

    if criteria.age:
        table = apply_age_filter(table, criteria.age, ctx, "visit_detail_end_date")
    table = apply_gender_filter(table, [], criteria.gender_cs, ctx)
    table = apply_provider_specialty_filter(
        table,
        None,
        criteria.provider_specialty_cs,
        ctx,
    )
    table = apply_care_site_filter(table, criteria.place_of_service_cs, ctx)
    table = apply_location_region_filter(
        table,
        care_site_column="care_site_id",
        location_codeset_id=criteria.place_of_service_location,
        start_column="visit_detail_start_date",
        end_column="visit_detail_end_date",
        ctx=ctx,
    )

    table = project_event_columns(
        table,
        primary_key="visit_detail_id",
        start_column="visit_detail_start_date",
        end_column="visit_detail_end_date",
        include_visit_occurrence=True,
    )

    events = standardize_output(
        table,
        primary_key="visit_detail_id",
        start_column="visit_detail_start_date",
        end_column="visit_detail_end_date",
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
