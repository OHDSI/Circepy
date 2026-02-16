from __future__ import annotations

import ibis

from ...cohortdefinition.criteria import Death
from ..build_context import BuildContext
from .common import (
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
)
from .patterns import apply_age_and_gender_filters, finalize_criteria_events
from .registry import register


@register("Death")
def build_death(criteria: Death, ctx: BuildContext):
    table = ctx.table("death")

    table = apply_codeset_filter(table, "cause_concept_id", criteria.codeset_id, ctx)

    table = apply_date_range(
        table, "death_date", getattr(criteria, "occurrence_start_date", None)
    )

    table = apply_concept_criteria(
        table,
        column="death_type_concept_id",
        concepts=criteria.death_type,
        selection=criteria.death_type_cs,
        ctx=ctx,
        exclude=bool(getattr(criteria, "death_type_exclude", False)),
    )

    if getattr(criteria, "death_source_concept", None) is not None:
        table = apply_codeset_filter(
            table,
            "cause_source_concept_id",
            int(criteria.death_source_concept),
            ctx,
        )

    table = apply_age_and_gender_filters(
        table,
        ctx=ctx,
        age_column=criteria.get_start_date_column(),
        age_range=criteria.age,
        genders=criteria.gender,
        gender_selection=criteria.gender_cs,
    )

    window = ibis.window(order_by=[table.person_id, table.death_date])
    table = table.mutate(death_event_id=ibis.row_number().over(window))

    events = finalize_criteria_events(
        table,
        criteria=criteria,
        ctx=ctx,
        primary_key="death_event_id",
        start_column="death_date",
        end_column="death_date",
    )
    return events
