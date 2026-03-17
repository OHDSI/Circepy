from __future__ import annotations

import ibis

from ...cohortdefinition.criteria import Death
from ..build_context import BuildContext
from .common import (
    apply_age_filter,
    apply_codeset_filter,
    apply_concept_criteria,
    apply_date_range,
    apply_gender_filter,
    standardize_output,
)
from .groups import apply_criteria_group
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

    if criteria.age:
        table = apply_age_filter(
            table, criteria.age, ctx, criteria.get_start_date_column()
        )
    table = apply_gender_filter(table, criteria.gender, criteria.gender_cs, ctx)

    window = ibis.window(order_by=[table.person_id, table.death_date])
    table = table.mutate(death_event_id=ibis.row_number().over(window))

    events = standardize_output(
        table,
        primary_key="death_event_id",
        start_column="death_date",
        end_column="death_date",
    )
    return apply_criteria_group(events, criteria.correlated_criteria, ctx)
