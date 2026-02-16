from __future__ import annotations

from ...cohortdefinition.criteria import Observation
from ..build_context import BuildContext
from .common import (
    apply_codeset_filter,
    apply_concept_criteria,
    apply_first_event,
    apply_numeric_range,
    apply_provider_specialty_filter,
    apply_text_filter,
    apply_visit_concept_filters,
)
from .patterns import (
    apply_age_and_gender_filters,
    apply_primary_concept_and_date_filters,
    finalize_criteria_events,
)
from .registry import register


@register("Observation")
def build_observation(criteria: Observation, ctx: BuildContext):
    table = ctx.table("observation")
    table = apply_primary_concept_and_date_filters(
        table,
        ctx=ctx,
        concept_column=criteria.get_concept_id_column(),
        codeset_id=criteria.codeset_id,
        start_column=criteria.get_start_date_column(),
        start_range=criteria.occurrence_start_date,
        end_column=criteria.get_end_date_column(),
        end_range=criteria.occurrence_end_date,
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

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key=criteria.get_primary_key_column(),
        start_column=criteria.get_start_date_column(),
        end_column=criteria.get_end_date_column(),
    )
    return events
