from __future__ import annotations

from ...cohortdefinition.criteria import DrugExposure
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
    coerce_concept_set_selection,
    standardize_output,
)
from .groups import apply_criteria_group
from .registry import register


@register("DrugExposure")
def build_drug_exposure(criteria: DrugExposure, ctx: BuildContext):
    table = ctx.table("drug_exposure")

    concept_column = criteria.get_concept_id_column()
    table = apply_codeset_filter(table, concept_column, criteria.codeset_id, ctx)
    if criteria.first:
        table = apply_first_event(table, criteria.get_start_date_column(), criteria.get_primary_key_column())

    table = apply_date_range(table, criteria.get_start_date_column(), criteria.occurrence_start_date)
    table = apply_date_range(table, criteria.get_end_date_column(), criteria.occurrence_end_date)

    table = apply_concept_criteria(
        table,
        column="drug_type_concept_id",
        concepts=criteria.drug_type,
        selection=criteria.drug_type_cs,
        ctx=ctx,
        exclude=bool(getattr(criteria, "drug_type_exclude", False)),
    )
    table = apply_concept_criteria(
        table,
        column="route_concept_id",
        concepts=criteria.route_concept,
        selection=criteria.route_concept_cs,
        ctx=ctx,
    )
    table = apply_concept_criteria(
        table,
        column="dose_unit_concept_id",
        concepts=getattr(criteria, "dose_unit", []),
        selection=getattr(criteria, "dose_unit_cs", None),
        ctx=ctx,
    )

    table = apply_numeric_range(table, "quantity", criteria.quantity)
    table = apply_numeric_range(table, "days_supply", criteria.days_supply)
    table = apply_numeric_range(table, "refills", criteria.refills)
    table = apply_text_filter(table, "stop_reason", getattr(criteria, "stop_reason", None))
    table = apply_text_filter(table, "lot_number", getattr(criteria, "lot_number", None))

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

    source_filter = getattr(criteria, "drug_source_concept", None)
    selection = coerce_concept_set_selection(source_filter)
    if selection is not None:
        table = apply_concept_criteria(
            table,
            column="drug_source_concept_id",
            concepts=None,
            selection=selection,
            ctx=ctx,
        )

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
