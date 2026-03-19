from __future__ import annotations

import ibis

from ..errors import UnsupportedFeatureError
from ..plan.schema import END_DATE, PERSON_ID, START_DATE
from .custom_era import apply_custom_era_end_strategy


def attach_observation_bounds(events, ctx):
    observation_period = ctx.table("observation_period").select(
        PERSON_ID,
        "observation_period_start_date",
        "observation_period_end_date",
    )
    joined = events.join(
        observation_period,
        (events[PERSON_ID] == observation_period[PERSON_ID])
        & (events[START_DATE] >= observation_period.observation_period_start_date.cast("date"))
        & (events[START_DATE] <= observation_period.observation_period_end_date.cast("date")),
    )
    return joined.select(
        *[joined[c] for c in events.columns],
        observation_period.observation_period_start_date.cast("date").name("op_start_date"),
        observation_period.observation_period_end_date.cast("date").name("op_end_date"),
    ).distinct()


def _apply_date_offset_strategy(with_bounds, strategy):
    offset = int(strategy.payload.get("offset", 0))
    date_field = str(strategy.payload.get("date_field", START_DATE)).lower()

    if date_field in {"startdate", START_DATE}:
        base_date = with_bounds[START_DATE]
    elif date_field in {"enddate", END_DATE}:
        base_date = with_bounds[END_DATE]
    else:
        raise UnsupportedFeatureError(
            f"Ibis executor end-strategy error: unsupported date_offset date field {date_field!r}."
        )

    candidate = base_date + ibis.interval(days=offset)
    return ibis.least(candidate, with_bounds.op_end_date)


def _replace_end_date(events, with_bounds, new_end_expr):
    projected = with_bounds.mutate(_new_end_date=new_end_expr)
    selected = projected.select(
        *[
            projected[c] if c != END_DATE else projected._new_end_date.cast("date").name(END_DATE)
            for c in events.columns
        ]
    )
    return selected


def apply_end_strategy(events, strategy, ctx):
    with_bounds = attach_observation_bounds(events, ctx)

    if strategy is None:
        return _replace_end_date(events, with_bounds, with_bounds.op_end_date)

    if strategy.kind == "date_offset":
        end_date_expr = _apply_date_offset_strategy(with_bounds, strategy)
        return _replace_end_date(events, with_bounds, end_date_expr)

    if strategy.kind == "custom_era":
        with_custom_eras = apply_custom_era_end_strategy(events, with_bounds, strategy, ctx)
        end_date_expr = ibis.least(
            ibis.coalesce(with_custom_eras._custom_era_end, with_custom_eras.op_end_date),
            with_custom_eras.op_end_date,
        )
        return _replace_end_date(events, with_custom_eras, end_date_expr)

    # Fallback: preserve default semantics of op_end_date clipping.
    return _replace_end_date(events, with_bounds, with_bounds.op_end_date)
