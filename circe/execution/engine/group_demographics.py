from __future__ import annotations

import ibis

from ..errors import UnsupportedFeatureError
from ..ibis.context import ExecutionContext
from ..normalize.groups import NormalizedDemographicCriteria
from ..plan.schema import EVENT_ID, PERSON_ID
from ..typing import Table


def _apply_numeric_predicate(expr, predicate):
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
            raise UnsupportedFeatureError(
                "Ibis executor group evaluation error: demographic numeric range "
                "'between' requires an extent value."
            )
        lower = min(value, extent)
        upper = max(value, extent)
        return (expr >= lower) & (expr <= upper)
    raise UnsupportedFeatureError(
        f"Ibis executor group evaluation error: unsupported demographic numeric range op {predicate.op!r}."
    )


def _apply_date_predicate(date_expr, predicate):
    op = (predicate.op or "eq").lower()
    value = predicate.value
    extent = predicate.extent

    if value is None:
        return ibis.literal(True)

    value_expr = ibis.literal(value).cast("date")

    if op in {"eq", "="}:
        return date_expr.cast("date") == value_expr
    if op in {"neq", "!=", "ne"}:
        return date_expr.cast("date") != value_expr
    if op in {"gt", ">"}:
        return date_expr.cast("date") > value_expr
    if op in {"gte", ">="}:
        return date_expr.cast("date") >= value_expr
    if op in {"lt", "<"}:
        return date_expr.cast("date") < value_expr
    if op in {"lte", "<="}:
        return date_expr.cast("date") <= value_expr
    if op in {"bt", "between"}:
        if extent is None:
            raise UnsupportedFeatureError(
                "Ibis executor group evaluation error: demographic date range "
                "'between' requires an extent value."
            )
        extent_expr = ibis.literal(extent).cast("date")
        lower = ibis.least(value_expr, extent_expr)
        upper = ibis.greatest(value_expr, extent_expr)
        return (date_expr.cast("date") >= lower) & (date_expr.cast("date") <= upper)
    raise UnsupportedFeatureError(
        f"Ibis executor group evaluation error: unsupported demographic date range op {predicate.op!r}."
    )


def _explicit_ids_table(concept_ids: tuple[int, ...]) -> Table:
    """Build a single-column ibis Table from explicit concept IDs, no memtable.

    Uses ``ibis.literal().name().as_table()`` with ``union()`` — generates
    ``SELECT id1 AS concept_id UNION ALL SELECT id2 AS concept_id ...``.
    """
    first = ibis.literal(int(concept_ids[0]), type="int64").name("concept_id").as_table()
    for cid in concept_ids[1:]:
        t = ibis.literal(int(cid), type="int64").name("concept_id").as_table()
        first = first.union(t, distinct=False)
    return first


def _demographic_concept_ids(
    *,
    explicit_ids: tuple[int, ...],
    codeset_id: int | None,
    ctx: ExecutionContext,
) -> Table | None:
    """Resolve concept IDs for a demographic filter.

    Returns an ibis Table with a single ``concept_id`` column, or ``None``
    if neither explicit IDs nor a codeset is provided (meaning no filter).
    """
    if not explicit_ids and codeset_id is None:
        return None
    parts: list[Table] = []
    if explicit_ids:
        parts.append(_explicit_ids_table(explicit_ids))
    if codeset_id is not None:
        parts.append(ctx.concept_set_table(codeset_id).select("concept_id").distinct())
    result = parts[0]
    for part in parts[1:]:
        result = result.union(part, distinct=True)
    return result


def demographic_match_keys(
    index_events: Table,
    demographic: NormalizedDemographicCriteria,
    ctx: ExecutionContext,
) -> Table:
    person_table = ctx.table("person")
    person = person_table.select(
        person_table.person_id.name("p_person_id"),
        "year_of_birth",
        "gender_concept_id",
        "race_concept_id",
        "ethnicity_concept_id",
    )
    joined = index_events.join(person, index_events.person_id == person.p_person_id)

    predicates = [ibis.literal(True)]
    if demographic.age is not None:
        event_date = joined.start_date.cast("date")
        age_years = event_date.year() - joined.year_of_birth
        predicates.append(_apply_numeric_predicate(age_years, demographic.age))

    gender_ids = _demographic_concept_ids(
        explicit_ids=demographic.gender_concept_ids,
        codeset_id=demographic.gender_codeset_id,
        ctx=ctx,
    )
    if gender_ids is not None:
        predicates.append(joined.gender_concept_id.isin(gender_ids.concept_id))

    race_ids = _demographic_concept_ids(
        explicit_ids=demographic.race_concept_ids,
        codeset_id=demographic.race_codeset_id,
        ctx=ctx,
    )
    if race_ids is not None:
        predicates.append(joined.race_concept_id.isin(race_ids.concept_id))

    ethnicity_ids = _demographic_concept_ids(
        explicit_ids=demographic.ethnicity_concept_ids,
        codeset_id=demographic.ethnicity_codeset_id,
        ctx=ctx,
    )
    if ethnicity_ids is not None:
        predicates.append(joined.ethnicity_concept_id.isin(ethnicity_ids.concept_id))

    if demographic.occurrence_start_date is not None:
        predicates.append(
            _apply_date_predicate(
                joined.start_date,
                demographic.occurrence_start_date,
            )
        )
    if demographic.occurrence_end_date is not None:
        predicates.append(
            _apply_date_predicate(
                joined.end_date,
                demographic.occurrence_end_date,
            )
        )

    predicate = predicates[0]
    for part in predicates[1:]:
        predicate = predicate & part

    matched = joined.filter(predicate)
    return matched.select(
        matched.person_id.name(PERSON_ID),
        matched.event_id.name(EVENT_ID),
    ).distinct()
