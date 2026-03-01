from __future__ import annotations

import ibis

from ..errors import CompilationError, UnsupportedFeatureError
from ..plan.events import (
    ApplyDateAdjustment,
    FilterByCodeset,
    FilterByConceptSet,
    FilterByDateRange,
    FilterByNumericRange,
    FilterByPersonAge,
    FilterByPersonEthnicity,
    FilterByPersonGender,
    FilterByPersonRace,
    FilterByText,
    JoinLocationRegion,
    KeepFirstPerPerson,
    RestrictToCorrelatedWindow,
    StandardizeEventShape,
)
from ..plan.predicates import DateRangePredicate, NumericRangePredicate
from ..plan.schema import END_DATE, PERSON_ID, START_DATE
from .context import ExecutionContext
from .person_filters import (
    apply_person_age_filter,
    apply_person_ethnicity_filter,
    apply_person_gender_filter,
    apply_person_race_filter,
)
from .standardize import standardize_event_table


def _apply_numeric_predicate(expr, predicate: NumericRangePredicate):
    op = (predicate.op or "eq").lower()
    value = predicate.value
    extent = predicate.extent

    if value is None:
        return ibis.literal(True)

    if op in {"eq", "="}:
        return expr == value
    if op in {"neq", "!=", "ne"}:
        return expr != value
    if op in {"gt", ">"}:
        return expr > value
    if op in {"gte", ">="}:
        return expr >= value
    if op in {"lt", "<"}:
        return expr < value
    if op in {"lte", "<="}:
        return expr <= value
    if op in {"bt", "between"}:
        if extent is None:
            raise CompilationError(
                "Ibis executor compilation error: numeric range 'between' "
                "requires an extent value."
            )
        lower = min(value, extent)
        upper = max(value, extent)
        return (expr >= lower) & (expr <= upper)

    raise CompilationError(
        "Ibis executor compilation error: unsupported numeric range op "
        f"{predicate.op!r}."
    )


def _apply_date_predicate(expr, predicate: DateRangePredicate):
    op = (predicate.op or "eq").lower()
    value = predicate.value
    extent = predicate.extent

    if value is None:
        return ibis.literal(True)

    value_expr = ibis.literal(value).cast("date")

    if op in {"eq", "="}:
        return expr.cast("date") == value_expr
    if op in {"neq", "!=", "ne"}:
        return expr.cast("date") != value_expr
    if op in {"gt", ">"}:
        return expr.cast("date") > value_expr
    if op in {"gte", ">="}:
        return expr.cast("date") >= value_expr
    if op in {"lt", "<"}:
        return expr.cast("date") < value_expr
    if op in {"lte", "<="}:
        return expr.cast("date") <= value_expr
    if op in {"bt", "between"}:
        if extent is None:
            raise CompilationError(
                "Ibis executor compilation error: date range 'between' "
                "requires an extent value."
            )
        extent_expr = ibis.literal(extent).cast("date")
        lower = ibis.least(value_expr, extent_expr)
        upper = ibis.greatest(value_expr, extent_expr)
        return (expr.cast("date") >= lower) & (expr.cast("date") <= upper)

    raise CompilationError(
        "Ibis executor compilation error: unsupported date range op "
        f"{predicate.op!r}."
    )


def apply_step(step, *, table, source, ctx: ExecutionContext):
    if isinstance(step, JoinLocationRegion):
        location = ctx.table("location").select(
            "location_id",
            step.region_column,
        )
        joined = table.join(
            location,
            table[step.location_id_column] == location.location_id,
        )
        return joined.select(
            *[joined[c] for c in table.columns],
            location[step.region_column].name(step.region_column),
        )

    if isinstance(step, FilterByCodeset):
        concept_ids = ctx.concept_ids_for_codeset(step.codeset_id)
        if not concept_ids:
            return table if step.exclude else table.limit(0)
        predicate = table[step.column].isin(concept_ids)
        return table.filter(~predicate if step.exclude else predicate)

    if isinstance(step, FilterByConceptSet):
        if not step.concept_ids:
            return table if step.exclude else table.limit(0)
        predicate = table[step.column].isin(step.concept_ids)
        return table.filter(~predicate if step.exclude else predicate)

    if isinstance(step, FilterByDateRange):
        return table.filter(_apply_date_predicate(table[step.column], step.predicate))

    if isinstance(step, FilterByNumericRange):
        return table.filter(
            _apply_numeric_predicate(table[step.column], step.predicate)
        )

    if isinstance(step, FilterByText):
        op = (step.op or "eq").lower()
        if step.text is None:
            return table
        if op in {"eq", "="}:
            return table.filter(table[step.column] == step.text)
        if op in {"neq", "!=", "ne"}:
            return table.filter(table[step.column] != step.text)
        if op in {"contains", "like"}:
            return table.filter(table[step.column].contains(step.text))
        raise CompilationError(
            "Ibis executor compilation error: unsupported text filter op "
            f"{step.op!r}."
        )

    if isinstance(step, FilterByPersonAge):
        return apply_person_age_filter(
            table,
            ctx,
            date_column=step.date_column,
            predicate=step.predicate,
        )

    if isinstance(step, FilterByPersonGender):
        return apply_person_gender_filter(
            table,
            ctx,
            concept_ids=step.concept_ids,
            codeset_id=step.codeset_id,
        )

    if isinstance(step, FilterByPersonRace):
        return apply_person_race_filter(
            table,
            ctx,
            concept_ids=step.concept_ids,
            codeset_id=step.codeset_id,
        )

    if isinstance(step, FilterByPersonEthnicity):
        return apply_person_ethnicity_filter(
            table,
            ctx,
            concept_ids=step.concept_ids,
            codeset_id=step.codeset_id,
        )

    if isinstance(step, KeepFirstPerPerson):
        order_by = [table[c] for c in step.order_by if c in table.columns]
        window = ibis.window(group_by=table[PERSON_ID], order_by=order_by)
        ranked = table.mutate(_exec_rn=ibis.row_number().over(window))
        return ranked.filter(ranked._exec_rn == 0).drop("_exec_rn")

    if isinstance(step, ApplyDateAdjustment):
        return table.mutate(
            **{
                START_DATE: (
                    table[START_DATE] + ibis.interval(days=step.start_offset_days)
                ),
                END_DATE: table[END_DATE] + ibis.interval(days=step.end_offset_days),
            }
        )

    if isinstance(step, RestrictToCorrelatedWindow):
        raise UnsupportedFeatureError(
            "Ibis executor compilation error: RestrictToCorrelatedWindow step "
            "is not implemented."
        )

    if isinstance(step, StandardizeEventShape):
        return standardize_event_table(
            table,
            source=source,
            criterion_type=step.criterion_type,
            criterion_index=step.criterion_index,
        )

    raise CompilationError(
        "Ibis executor compilation error: unsupported plan step "
        f"{step.__class__.__name__}."
    )
