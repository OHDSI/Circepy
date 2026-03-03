from __future__ import annotations

from ...cohortdefinition.criteria import VisitOccurrence
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
    project_event_columns,
    standardize_output,
)
from .groups import apply_criteria_group
from ...extensions import register_ibis_builder


@register_ibis_builder("VisitOccurrence")
def build_visit_occurrence(criteria: VisitOccurrence, ctx: BuildContext):
    table = ctx.table("visit_occurrence")

    concept_column = criteria.get_concept_id_column()
    table = apply_codeset_filter(table, concept_column, criteria.codeset_id, ctx)

    table = apply_date_range(
        table, criteria.get_start_date_column(), criteria.occurrence_start_date
    )
    table = apply_date_range(
        table, criteria.get_end_date_column(), criteria.occurrence_end_date
    )

    table = apply_concept_criteria(
        table,
        column="visit_type_concept_id",
        concepts=criteria.visit_type,
        selection=criteria.visit_type_cs,
        ctx=ctx,
        exclude=bool(criteria.visit_type_exclude),
    )

    table = apply_provider_specialty_filter(
        table,
        criteria.provider_specialty,
        criteria.provider_specialty_cs,
        ctx,
    )
    table = apply_concept_criteria(
        table,
        column="place_of_service_concept_id",
        concepts=criteria.place_of_service,
        selection=criteria.place_of_service_cs,
        ctx=ctx,
    )
    if criteria.visit_length:
        table = apply_numeric_range(table, "visit_length", criteria.visit_length)

    if criteria.age:
        table = apply_age_filter(
            table, criteria.age, ctx, criteria.get_start_date_column()
        )
    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)

    if criteria.visit_source_concept is not None:
        table = apply_codeset_filter(
            table, "visit_source_concept_id", criteria.visit_source_concept, ctx
        )

    if criteria.first:
        table = apply_first_event(
            table, criteria.get_start_date_column(), criteria.get_primary_key_column()
        )

    table = project_event_columns(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
        include_visit_occurrence=True,
    )

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
