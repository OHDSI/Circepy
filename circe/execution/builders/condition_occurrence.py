from __future__ import annotations

from ...cohortdefinition.criteria import ConditionOccurrence
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_first_event,
    apply_gender_filter,
    apply_visit_concept_filters,
    coerce_concept_set_selection,
    standardize_output,
)
from .groups import apply_criteria_group
from ...extensions import register_ibis_builder


@register_ibis_builder("ConditionOccurrence")
def build_condition_occurrence(criteria: ConditionOccurrence, ctx: BuildContext):
    table = ctx.table("condition_occurrence")

    concept_column = criteria.get_concept_id_column()
    table = apply_codeset_filter(table, concept_column, criteria.codeset_id, ctx)
    if criteria.first:
        table = apply_first_event(
            table, criteria.get_start_date_column(), criteria.get_primary_key_column()
        )

    table = apply_date_range(
        table, criteria.get_start_date_column(), criteria.occurrence_start_date
    )
    table = apply_date_range(
        table, criteria.get_end_date_column(), criteria.occurrence_end_date
    )

    table = apply_concept_criteria(
        table,
        column="condition_type_concept_id",
        concepts=criteria.condition_type,
        selection=criteria.condition_type_cs,
        ctx=ctx,
        exclude=bool(criteria.condition_type_exclude),
    )

    table = apply_concept_criteria(
        table,
        column="condition_status_concept_id",
        concepts=getattr(criteria, "condition_status", None),
        selection=None,
        ctx=ctx,
    )

    if criteria.age:
        table = apply_age_filter(
            table, criteria.age, ctx, criteria.get_start_date_column()
        )
    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)

    source_filter = getattr(criteria, "condition_source_concept", None)
    selection = coerce_concept_set_selection(source_filter)
    if selection is not None:
        table = apply_concept_criteria(
            table,
            column="condition_source_concept_id",
            concepts=None,
            selection=selection,
            ctx=ctx,
        )

    visit_source = getattr(criteria, "visit_source_concept", None)
    needs_visit_filters = bool(
        criteria.visit_type or criteria.visit_type_cs or visit_source is not None
    )
    if needs_visit_filters:
        visit = ctx.table("visit_occurrence").select(
            "person_id",
            "visit_occurrence_id",
            "visit_concept_id",
            "visit_source_concept_id",
        )
        table = table.join(
            visit,
            (table.visit_occurrence_id == visit.visit_occurrence_id)
            & (table.person_id == visit.person_id),
        )
        table = apply_visit_concept_filters(
            table, criteria.visit_type, criteria.visit_type_cs, ctx
        )
        if visit_source is not None:
            table = table.filter(table.visit_source_concept_id == int(visit_source))

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
