from __future__ import annotations

import ibis

from ..errors import UnsupportedFeatureError
from ..plan.schema import PERSON_ID, START_DATE


def _effective_drug_exposure_end_date(drug_exposure, *, days_supply_override: int | None):
    start_date = drug_exposure.drug_exposure_start_date.cast("date")
    raw_end_date = drug_exposure.drug_exposure_end_date.cast("date")

    if days_supply_override is not None:
        return start_date + ibis.interval(days=int(days_supply_override))

    days_supply = drug_exposure.days_supply.cast("int64")
    supply_end_date = start_date + days_supply.as_interval("D")
    return ibis.coalesce(raw_end_date, supply_end_date, start_date + ibis.interval(days=1))


def _build_custom_eras(exposures, *, gap_days: int, offset: int):
    padded_end_days = int(gap_days) + int(offset)
    padded = exposures.mutate(
        _padded_end_date=exposures.exposure_end_date + ibis.interval(days=padded_end_days)
    )

    ordered_window = ibis.window(group_by=padded.person_id, order_by=[padded.exposure_start_date])
    with_cummax = padded.mutate(_cummax_padded_end=padded._padded_end_date.max().over(ordered_window))
    with_prev = with_cummax.mutate(
        _prev_max_padded_end=with_cummax._cummax_padded_end.lag().over(ordered_window)
    )
    marked = with_prev.mutate(
        _is_new_group=ibis.ifelse(
            with_prev._prev_max_padded_end.isnull()
            | (with_prev._prev_max_padded_end < with_prev.exposure_start_date),
            ibis.literal(1, type="int64"),
            ibis.literal(0, type="int64"),
        )
    )
    grouped = marked.mutate(_group_idx=marked._is_new_group.sum().over(ordered_window))

    collapsed = grouped.group_by(grouped.person_id, grouped._group_idx).aggregate(
        era_start_date=grouped.exposure_start_date.min(),
        _max_padded_end=grouped._padded_end_date.max(),
    )
    return collapsed.select(
        collapsed.person_id.cast("int64").name(PERSON_ID),
        collapsed.era_start_date.cast("date").name("era_start_date"),
        (collapsed._max_padded_end - ibis.interval(days=int(gap_days))).cast("date").name("era_end_date"),
    )


def apply_custom_era_end_strategy(events, with_bounds, strategy, ctx):
    drug_codeset_id = strategy.payload.get("drug_codeset_id")
    if drug_codeset_id is None:
        raise UnsupportedFeatureError(
            "Ibis executor end-strategy error: custom_era requires drug_codeset_id."
        )

    gap_days = int(strategy.payload.get("gap_days", 0))
    if gap_days < 0:
        raise UnsupportedFeatureError(
            f"Ibis executor end-strategy error: custom_era gap_days must be non-negative, got {gap_days}."
        )

    offset = int(strategy.payload.get("offset", 0))
    days_supply_override = strategy.payload.get("days_supply_override")
    if days_supply_override is not None:
        days_supply_override = int(days_supply_override)

    concept_ids = ctx.concept_ids_for_codeset(int(drug_codeset_id))
    if not concept_ids:
        return with_bounds.mutate(_custom_era_end=ibis.null().cast("date"))

    persons = with_bounds.select(with_bounds[PERSON_ID].cast("int64").name(PERSON_ID)).distinct()
    drug_exposure = ctx.table("drug_exposure")
    joined = drug_exposure.join(persons, drug_exposure.person_id == persons.person_id)
    filtered = joined.filter(
        joined.drug_concept_id.isin(concept_ids) | joined.drug_source_concept_id.isin(concept_ids)
    )

    exposures = filtered.select(
        joined.person_id.cast("int64").name(PERSON_ID),
        joined.drug_exposure_start_date.cast("date").name("exposure_start_date"),
        _effective_drug_exposure_end_date(
            joined,
            days_supply_override=days_supply_override,
        )
        .cast("date")
        .name("exposure_end_date"),
    )
    exposures = exposures.filter(
        exposures.exposure_start_date.notnull() & exposures.exposure_end_date.notnull()
    ).distinct()

    eras = _build_custom_eras(exposures, gap_days=gap_days, offset=offset)
    matched = with_bounds.left_join(
        eras,
        (with_bounds[PERSON_ID] == eras[PERSON_ID])
        & (with_bounds[START_DATE] >= eras.era_start_date)
        & (with_bounds[START_DATE] <= eras.era_end_date),
    )
    grouped = matched.group_by(*[matched[c] for c in with_bounds.columns]).aggregate(
        _custom_era_end=matched.era_end_date.min()
    )
    return grouped
