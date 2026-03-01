from __future__ import annotations

import ibis

from ..errors import UnsupportedFeatureError


def attach_observation_bounds(events, ctx):
    observation_period = ctx.table("observation_period").select(
        "person_id",
        "observation_period_start_date",
        "observation_period_end_date",
    )
    joined = events.join(
        observation_period,
        (events.person_id == observation_period.person_id)
        & (
            events.start_date
            >= observation_period.observation_period_start_date.cast("date")
        )
        & (
            events.start_date <= observation_period.observation_period_end_date.cast("date")
        ),
    )
    return joined.select(
        *[joined[c] for c in events.columns],
        observation_period.observation_period_start_date.cast("date").name("op_start_date"),
        observation_period.observation_period_end_date.cast("date").name("op_end_date"),
    ).distinct()


def _apply_date_offset_strategy(with_bounds, strategy):
    offset = int(strategy.payload.get("offset", 0))
    date_field = str(strategy.payload.get("date_field", "start_date")).lower()

    if date_field in {"startdate", "start_date"}:
        base_date = with_bounds.start_date
    elif date_field in {"enddate", "end_date"}:
        base_date = with_bounds.end_date
    else:
        raise UnsupportedFeatureError(
            f"Unsupported date field for date_offset strategy: {date_field}"
        )

    candidate = base_date + ibis.interval(days=offset)
    return ibis.least(candidate, with_bounds.op_end_date)


def _replace_end_date(events, with_bounds, new_end_expr):
    projected = with_bounds.mutate(_new_end_date=new_end_expr)
    selected = projected.select(
        *[
            projected[c]
            if c != "end_date"
            else projected._new_end_date.cast("date").name("end_date")
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
        raise UnsupportedFeatureError(
            "custom_era end strategy is not implemented in the Ibis executor."
        )

    # Fallback: preserve default semantics of op_end_date clipping.
    return _replace_end_date(events, with_bounds, with_bounds.op_end_date)
