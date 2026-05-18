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


def _demographic_concept_ids(
    *,
    explicit_ids: tuple[int, ...],
    codeset_id: int | None,
    ctx: ExecutionContext,
) -> tuple[int, ...]:
    """Resolve concept IDs for a demographic filter.

    Returns a Python tuple of concept IDs.  Demographic sets are tiny (1-5
    IDs) so this is cheap and avoids join complexity.
    """
    all_ids = list(explicit_ids)
    if codeset_id is not None:
        t = ctx.concept_set_table(codeset_id)
        for row in t.select("concept_id").distinct().to_pandas().itertuples():
            cid = row.concept_id
            if cid not in all_ids:
                all_ids.append(cid)
    return tuple(all_ids)


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
    if gender_ids:
        predicates.append(joined.gender_concept_id.isin(gender_ids))

    race_ids = _demographic_concept_ids(
        explicit_ids=demographic.race_concept_ids,
        codeset_id=demographic.race_codeset_id,
        ctx=ctx,
    )
    if race_ids:
        predicates.append(joined.race_concept_id.isin(race_ids))

    ethnicity_ids = _demographic_concept_ids(
        explicit_ids=demographic.ethnicity_concept_ids,
        codeset_id=demographic.ethnicity_codeset_id,
        ctx=ctx,
    )
    if ethnicity_ids:
        predicates.append(joined.ethnicity_concept_id.isin(ethnicity_ids))

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
