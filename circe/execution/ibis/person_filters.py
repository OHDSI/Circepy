from __future__ import annotations

import ibis

from ..errors import CompilationError
from ..plan.predicates import NumericRangePredicate
from .context import ExecutionContext


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
            raise CompilationError("Between numeric range requires extent.")
        lower = min(value, extent)
        upper = max(value, extent)
        return (expr >= lower) & (expr <= upper)

    raise CompilationError(f"Unsupported numeric range op: {predicate.op}")


def apply_person_age_filter(table, ctx: ExecutionContext, *, date_column: str, predicate):
    person = ctx.table("person").select(
        "person_id",
        "year_of_birth",
    )
    joined = table.join(person, table.person_id == person.person_id)
    event_date = joined[date_column].cast("date")
    age_years = event_date.year() - joined.year_of_birth
    filtered = joined.filter(_apply_numeric_predicate(age_years, predicate))
    return filtered.select(*[filtered[c] for c in table.columns])


def apply_person_gender_filter(
    table,
    ctx: ExecutionContext,
    *,
    concept_ids: tuple[int, ...],
    codeset_id: int | None,
):
    all_ids = list(concept_ids)
    if codeset_id is not None:
        for cid in ctx.concept_ids_for_codeset(codeset_id):
            if cid not in all_ids:
                all_ids.append(cid)

    if not all_ids:
        return table

    person = ctx.table("person").select("person_id", "gender_concept_id")
    joined = table.join(person, table.person_id == person.person_id)
    filtered = joined.filter(joined.gender_concept_id.isin(all_ids))
    return filtered.select(*[filtered[c] for c in table.columns])
