from __future__ import annotations

from ...cohortdefinition.criteria import Specimen
from ..build_context import BuildContext
from .common import (
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_numeric_range,
    apply_text_filter,
)
from .patterns import apply_age_and_gender_filters, finalize_criteria_events
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

    table = apply_age_and_gender_filters(
        table,
        ctx=ctx,
        age_column="specimen_date",
        age_range=criteria.age,
        genders=criteria.gender,
        gender_selection=criteria.gender_cs,
    )

    if criteria.first:
        table = apply_first_event(table, "specimen_date", "specimen_id")

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key="specimen_id",
        start_column="specimen_date",
        end_column="specimen_date",
    )
    return events
