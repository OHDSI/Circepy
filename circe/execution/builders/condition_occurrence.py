from __future__ import annotations

from ...cohortdefinition.criteria import ConditionOccurrence
from ..build_context import BuildContext
from .common import (
    apply_concept_criteria,
    apply_first_event,
    apply_visit_concept_filters,
    coerce_concept_set_selection,
)
from .patterns import (
    apply_age_and_gender_filters,
    apply_primary_concept_and_date_filters,
    finalize_criteria_events,
)
from .registry import register


@register("ConditionOccurrence")
def build_condition_occurrence(criteria: ConditionOccurrence, ctx: BuildContext):
    table = ctx.table("condition_occurrence")

    concept_column = criteria.get_concept_id_column()
    table = apply_primary_concept_and_date_filters(
        table,
        ctx=ctx,
        concept_column=concept_column,
        codeset_id=criteria.codeset_id,
        start_column=criteria.get_start_date_column(),
        start_range=criteria.occurrence_start_date,
        end_column=criteria.get_end_date_column(),
        end_range=criteria.occurrence_end_date,
    )
    if criteria.first:
        table = apply_first_event(
            table, criteria.get_start_date_column(), criteria.get_primary_key_column()
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

    table = apply_age_and_gender_filters(
        table,
        ctx=ctx,
        age_column=criteria.get_start_date_column(),
        age_range=criteria.age,
        genders=criteria.gender,
        gender_selection=criteria.gender_cs,
    )

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

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return events
