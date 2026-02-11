from __future__ import annotations

from ...cohortdefinition.criteria import Specimen
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_gender_filter,
    apply_numeric_range,
    apply_text_filter,
    standardize_output,
)
from .groups import apply_criteria_group
from .registry import register


@register("Specimen")
def build_specimen(criteria: Specimen, ctx: BuildContext):
    table = ctx.table("specimen")

    table = apply_codeset_filter(table, "specimen_concept_id", criteria.codeset_id, ctx)
    table = apply_date_range(table, "specimen_date", criteria.occurrence_start_date)

    table = apply_concept_criteria(
        table,
        column="specimen_type_concept_id",
        concepts=criteria.specimen_type,
        selection=criteria.specimen_type_cs,
        ctx=ctx,
        exclude=bool(criteria.specimen_type_exclude),
    )

    table = apply_numeric_range(table, "quantity", criteria.quantity)

    table = apply_concept_criteria(
        table,
        column="unit_concept_id",
        concepts=criteria.unit,
        selection=criteria.unit_cs,
        ctx=ctx,
    )

    table = apply_concept_criteria(
        table,
        column="anatomic_site_concept_id",
        concepts=criteria.anatomic_site,
        selection=criteria.anatomic_site_cs,
        ctx=ctx,
    )

    table = apply_concept_criteria(
        table,
        column="disease_status_concept_id",
        concepts=criteria.disease_status,
        selection=criteria.disease_status_cs,
        ctx=ctx,
    )

    table = apply_text_filter(table, "specimen_source_id", criteria.source_id)
    if criteria.specimen_source_concept is not None:
        table = apply_codeset_filter(
            table,
            "specimen_source_concept_id",
            criteria.specimen_source_concept,
            ctx,
        )

    if criteria.age:
        table = apply_age_filter(table, criteria.age, ctx, "specimen_date")
    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)

    if criteria.first:
        table = apply_first_event(table, "specimen_date", "specimen_id")

    events = standardize_output(
        table,
        primary_key="specimen_id",
        start_column="specimen_date",
        end_column="specimen_date",
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
