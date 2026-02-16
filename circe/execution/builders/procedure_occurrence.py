from __future__ import annotations

from ...cohortdefinition.criteria import ProcedureOccurrence
from ..build_context import BuildContext
from .common import (
    apply_codeset_filter,
    apply_concept_criteria,
    apply_first_event,
    apply_numeric_range,
    apply_provider_specialty_filter,
    apply_visit_concept_filters,
)
from .patterns import (
    apply_age_and_gender_filters,
    apply_primary_concept_and_date_filters,
    finalize_criteria_events,
)
from .registry import register


@register("ProcedureOccurrence")
def build_procedure_occurrence(criteria: ProcedureOccurrence, ctx: BuildContext):
    table = ctx.table("procedure_occurrence")

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
        column="procedure_type_concept_id",
        concepts=criteria.procedure_type,
        selection=criteria.procedure_type_cs,
        ctx=ctx,
        exclude=bool(criteria.procedure_type_exclude),
    )

    table = apply_concept_criteria(
        table,
        column="modifier_concept_id",
        concepts=criteria.modifier,
        selection=criteria.modifier_cs,
        ctx=ctx,
    )

    table = apply_numeric_range(table, "quantity", criteria.quantity)

    table = apply_age_and_gender_filters(
        table,
        ctx=ctx,
        age_column=criteria.get_start_date_column(),
        age_range=criteria.age,
        genders=criteria.gender,
        gender_selection=criteria.gender_cs,
    )
    table = apply_provider_specialty_filter(
        table,
        getattr(criteria, "provider_specialty", None),
        getattr(criteria, "provider_specialty_cs", None),
        ctx,
        provider_column="provider_id",
    )
    table = apply_visit_concept_filters(
        table, criteria.visit_type, criteria.visit_type_cs, ctx
    )

    if criteria.procedure_source_concept is not None:
        table = apply_codeset_filter(
            table,
            "procedure_source_concept_id",
            criteria.procedure_source_concept,
            ctx,
        )

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return events
