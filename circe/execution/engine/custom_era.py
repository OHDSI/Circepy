from __future__ import annotations

import ibis

from ..plan.schema import PERSON_ID, START_DATE
from .end_strategy import _replace_end_date, attach_observation_bounds


def _compute_exposure_end_date(table, *, days_supply_override: int | None):
    start = table["drug_exposure_start_date"].cast("date")

    if days_supply_override is not None:
        return start + ibis.interval(days=days_supply_override)

    raw_end = (
        table["drug_exposure_end_date"].cast("date")
        if "drug_exposure_end_date" in table.columns
        else ibis.null().cast("date")
    )
    days_supply = (
        table["days_supply"].cast("int64") if "days_supply" in table.columns else ibis.null().cast("int64")
    )
    supply_end = start + days_supply.as_interval("D")

    return ibis.coalesce(raw_end, supply_end, start + ibis.interval(days=1))


def _compute_eras(exposures, *, gap_days: int, offset: int):
    padded = exposures.mutate(
        _padded_end=(exposures._exposure_end + ibis.interval(days=int(gap_days + offset)))
    )

    ordering = [
        padded.start_date,
        padded._padded_end.desc(),
        padded._exposure_end.desc(),
    ]

    cumulative_window = ibis.cumulative_window(group_by=padded.person_id, order_by=ordering)
    ordered_window = ibis.window(group_by=padded.person_id, order_by=ordering)

    with_cummax = padded.mutate(_cummax_padded_end=padded._padded_end.max().over(cumulative_window))

    with_prev = with_cummax.mutate(_prev_max=with_cummax._cummax_padded_end.lag().over(ordered_window))

    marked = with_prev.mutate(
        _is_new=ibis.ifelse(
            with_prev._prev_max.isnull() | (with_prev._prev_max < with_prev.start_date),
            ibis.literal(1, type="int64"),
            ibis.literal(0, type="int64"),
        )
    )

    group_window = ibis.cumulative_window(
        group_by=marked.person_id,
        order_by=[
            marked.start_date,
            marked._padded_end.desc(),
            marked._exposure_end.desc(),
            marked._is_new.desc(),
        ],
    )
    era_indexed = marked.mutate(_era_id=marked._is_new.sum().over(group_window))

    collapsed = era_indexed.group_by(era_indexed.person_id, era_indexed._era_id).aggregate(
        era_start_date=era_indexed.start_date.min(),
        _max_padded_end=era_indexed._padded_end.max(),
    )

    return collapsed.select(
        collapsed.person_id.cast("int64").name(PERSON_ID),
        collapsed.era_start_date.cast("date").name("era_start_date"),
        (collapsed._max_padded_end - ibis.interval(days=int(gap_days))).cast("date").name("era_end_date"),
    )


def compute_drug_eras(
    ctx,
    *,
    drug_codeset_id: int,
    gap_days: int,
    offset: int,
    days_supply_override: int | None,
    cohort_person_ids=None,
):
    concept_table = ctx.concept_set_table(drug_codeset_id)

    de = ctx.table("drug_exposure")
    if cohort_person_ids is not None:
        de = de.semi_join(
            cohort_person_ids.select(cohort_person_ids.person_id).distinct(),
            predicates=[de.person_id == cohort_person_ids.person_id],
        )

    has_source = "drug_source_concept_id" in de.columns
    filtered = de.semi_join(concept_table, de.drug_concept_id == concept_table.concept_id)
    if has_source:
        source_matches = de.semi_join(concept_table, de.drug_source_concept_id == concept_table.concept_id)
        filtered = filtered.union(source_matches, distinct=True)

    prepared = filtered.select(
        filtered.person_id.cast("int64").name("person_id"),
        filtered.drug_exposure_start_date.cast("date").name("start_date"),
        _compute_exposure_end_date(filtered, days_supply_override=days_supply_override).name("_exposure_end"),
    )

    return _compute_eras(prepared, gap_days=gap_days, offset=offset)


def apply_custom_era_strategy(events, strategy, ctx):
    payload = strategy.payload
    drug_codeset_id = payload["drug_codeset_id"]
    gap_days = payload["gap_days"]
    offset = payload["offset"]
    days_supply_override = payload.get("days_supply_override")

    if drug_codeset_id is None:
        raise RuntimeError("Drug Codeset ID cannot be NULL.")

    cohort_person_ids = events.select(events.person_id).distinct()

    eras = compute_drug_eras(
        ctx,
        drug_codeset_id=drug_codeset_id,
        gap_days=gap_days,
        offset=offset,
        days_supply_override=days_supply_override,
        cohort_person_ids=cohort_person_ids,
    )

    eras_for_join = eras.select(
        eras.person_id.name("_era_person_id"),
        eras.era_start_date,
        eras.era_end_date,
    )

    with_bounds = attach_observation_bounds(events, ctx)

    joined = with_bounds.left_join(
        eras_for_join,
        predicates=[
            with_bounds.person_id == eras_for_join._era_person_id,
            with_bounds[START_DATE] >= eras_for_join.era_start_date,
            with_bounds[START_DATE] <= eras_for_join.era_end_date,
        ],
    )

    event_window = ibis.window(
        group_by=[joined.person_id, joined.event_id],
        order_by=[joined.era_end_date.desc()],
    )
    ranked = joined.mutate(_rn=ibis.row_number().over(event_window))
    one_per_event = ranked.filter(ranked._rn == 0)

    effective_end = ibis.coalesce(
        one_per_event.era_end_date,
        one_per_event.op_end_date,
    )
    final_end = ibis.least(effective_end, one_per_event.op_end_date)

    return _replace_end_date(events, one_per_event, final_end)
