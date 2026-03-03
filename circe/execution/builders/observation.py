from __future__ import annotations

from ...cohortdefinition.criteria import Observation
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
from ...extensions import register_ibis_builder


@register_ibis_builder("Observation")
def build_observation(criteria: Observation, ctx: BuildContext):
    table = ctx.table("observation")
    table = apply_codeset_filter(
        table, criteria.get_concept_id_column(), criteria.codeset_id, ctx
    )

    table = apply_date_range(
        table, criteria.get_start_date_column(), criteria.occurrence_start_date
    )
    table = apply_date_range(
        table, criteria.get_end_date_column(), criteria.occurrence_end_date
    )

    table = apply_concept_criteria(
        table,
        column="observation_type_concept_id",
        concepts=criteria.observation_type,
        selection=criteria.observation_type_cs,
        ctx=ctx,
        exclude=bool(criteria.observation_type_exclude),
    )

    table = apply_concept_criteria(
        table,
        column="qualifier_concept_id",
        concepts=criteria.qualifier,
        selection=criteria.qualifier_cs,
        ctx=ctx,
    )

    table = apply_concept_criteria(
        table,
        column="unit_concept_id",
        concepts=criteria.unit,
        selection=criteria.unit_cs,
        ctx=ctx,
    )

    table = apply_concept_criteria(
        table,
        column="value_as_concept_id",
        concepts=criteria.value_as_concept,
        selection=criteria.value_as_concept_cs,
        ctx=ctx,
    )

    table = apply_numeric_range(table, "value_as_number", criteria.value_as_number)
    table = apply_text_filter(table, "value_as_string", criteria.value_as_string)

    if criteria.age:
        table = apply_age_filter(
            table, criteria.age, ctx, criteria.get_start_date_column()
        )
    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)
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
    if criteria.observation_source_concept is not None:
        table = apply_codeset_filter(
            table,
            "observation_source_concept_id",
            criteria.observation_source_concept,
            ctx,
        )

    if criteria.first:
        table = apply_first_event(
            table, criteria.get_start_date_column(), criteria.get_primary_key_column()
        )

    events = standardize_output(
        table,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
