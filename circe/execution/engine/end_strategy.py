from __future__ import annotations

import ibis

from ..errors import UnsupportedFeatureError
from ..plan.schema import END_DATE, OP_END_DATE, OP_START_DATE, PERSON_ID, START_DATE


def attach_observation_bounds(events, ctx):
    """Attach observation period bounds to events.

    If events already carry op_start_date/op_end_date from the primary events
    stage, use those directly (avoiding a re-join that creates duplicates when
    overlapping OPs exist). Falls back to a re-join only if the columns are missing.
    """
    if OP_START_DATE in events.columns and OP_END_DATE in events.columns:
        return events

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
        observation_period.observation_period_start_date.cast("date").name(OP_START_DATE),
        observation_period.observation_period_end_date.cast("date").name(OP_END_DATE),
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
    return ibis.least(candidate, with_bounds[OP_END_DATE])


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
        return _replace_end_date(events, with_bounds, with_bounds[OP_END_DATE])

    if strategy.kind == "date_offset":
        end_date_expr = _apply_date_offset_strategy(with_bounds, strategy)
        return _replace_end_date(events, with_bounds, end_date_expr)

    if strategy.kind == "custom_era":
        from .custom_era import apply_custom_era_strategy

        return apply_custom_era_strategy(events, strategy, ctx)

    # Fallback: preserve default semantics of op_end_date clipping.
    return _replace_end_date(events, with_bounds, with_bounds[OP_END_DATE])
