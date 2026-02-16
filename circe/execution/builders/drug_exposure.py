from __future__ import annotations

from ...cohortdefinition.criteria import DrugExposure
from ..build_context import BuildContext
from .common import (
    apply_concept_criteria,
    apply_first_event,
    apply_numeric_range,
    apply_provider_specialty_filter,
    apply_text_filter,
    apply_visit_concept_filters,
    coerce_concept_set_selection,
)
from .patterns import (
    apply_age_and_gender_filters,
    apply_primary_concept_and_date_filters,
    finalize_criteria_events,
)
from .registry import register


@register("DrugExposure")
def build_drug_exposure(criteria: DrugExposure, ctx: BuildContext):
    table = ctx.table("drug_exposure")

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
    table = apply_text_filter(
        table, "stop_reason", getattr(criteria, "stop_reason", None)
    )
    table = apply_text_filter(
        table, "lot_number", getattr(criteria, "lot_number", None)
    )

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

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return events
