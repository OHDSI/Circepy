from __future__ import annotations

from ...cohortdefinition.criteria import ProcedureOccurrence
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import (
    append_concept_filters,
    append_numeric_filter,
    build_standard_domain_plan,
    lower_common_steps,
)


def lower_procedure_occurrence(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria
    if not isinstance(raw, ProcedureOccurrence):
        raise TypeError("lower_procedure_occurrence requires ProcedureOccurrence criteria")

    steps = lower_common_steps(criterion)

    append_concept_filters(
        steps,
        column="procedure_type_concept_id",
        concepts=raw.procedure_type,
        codeset_selection=raw.procedure_type_cs,
        exclude=bool(raw.procedure_type_exclude),
    )
    append_concept_filters(
        steps,
        column="modifier_concept_id",
        concepts=raw.modifier,
        codeset_selection=raw.modifier_cs,
    )
    append_numeric_filter(steps, column="quantity", value=raw.quantity)

    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )
