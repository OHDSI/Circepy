from __future__ import annotations

from ...cohortdefinition.criteria import DeviceExposure
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_gender_filter,
    apply_numeric_range,
    apply_provider_specialty_filter,
    apply_text_filter,
    apply_visit_concept_filters,
    standardize_output,
)
from .groups import apply_criteria_group
from .registry import register


@register("DeviceExposure")
def build_device_exposure(criteria: DeviceExposure, ctx: BuildContext):
    table = ctx.table("device_exposure")

    concept_column = criteria.get_concept_id_column()
    table = apply_codeset_filter(table, concept_column, criteria.codeset_id, ctx)

    table = apply_date_range(table, criteria.get_start_date_column(), criteria.occurrence_start_date)
    table = apply_date_range(table, criteria.get_end_date_column(), criteria.occurrence_end_date)

    table = apply_concept_criteria(
        table,
        column="device_type_concept_id",
        concepts=criteria.device_type,
        selection=criteria.device_type_cs,
        ctx=ctx,
        exclude=bool(criteria.device_type_exclude),
    )

    table = apply_numeric_range(table, "quantity", criteria.quantity)
    table = apply_text_filter(table, "unique_device_id", getattr(criteria, "unique_device_id", None))

    if criteria.age:
        table = apply_age_filter(table, criteria.age, ctx, criteria.get_start_date_column())
    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)
    table = apply_provider_specialty_filter(
        table,
        getattr(criteria, "provider_specialty", None),
        getattr(criteria, "provider_specialty_cs", None),
        ctx,
        provider_column="provider_id",
    )
    table = apply_visit_concept_filters(table, criteria.visit_type, criteria.visit_type_cs, ctx)
    if criteria.device_source_concept is not None:
        table = apply_codeset_filter(
            table,
            "device_source_concept_id",
            criteria.device_source_concept,
            ctx,
        )

    if criteria.first:
        table = apply_first_event(table, criteria.get_start_date_column(), criteria.get_primary_key_column())

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
