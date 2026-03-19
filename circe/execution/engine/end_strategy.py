from __future__ import annotations

import ibis

from ..errors import UnsupportedFeatureError
from ..plan.schema import END_DATE, PERSON_ID, START_DATE

# Import custom era functions (conditional to avoid breaking if sqlglot not installed)
try:
    from .custom_era import apply_custom_era, validate_custom_era_support

    CUSTOM_ERA_AVAILABLE = True
except ImportError:
    CUSTOM_ERA_AVAILABLE = False


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
        # Check if custom era implementation is available
        if not CUSTOM_ERA_AVAILABLE:
            raise UnsupportedFeatureError(
                "Custom era requires sqlglot package. Install with: pip install 'ohdsi-circe-python-alpha[ibis]'"
            )

        # Validate backend supports custom era
        if not validate_custom_era_support(ctx.backend):
            raise UnsupportedFeatureError(
                f"Custom era not supported for backend: {ctx.backend.name}. "
                "Supported backends: duckdb, postgres, spark, databricks, snowflake"
            )

        # Extract custom era parameters from strategy
        gap_days = int(strategy.payload.get("gap_days", 0))
        offset = int(strategy.payload.get("offset", 0))

        # Apply custom era using SQLGlot transpilation
        # Note: Custom era replaces end_date with era end, so we use the events directly
        eras = apply_custom_era(
            backend=ctx.backend,
            events=events,
            gap_days=gap_days,
            offset_start=0,  # Custom era typically doesn't offset start
            offset_end=offset,
            schema=ctx.results_schema,
            debug=False,  # Set to True for SQL debugging
        )

        return eras

    # Fallback: preserve default semantics of op_end_date clipping.
    return _replace_end_date(events, with_bounds, with_bounds.op_end_date)
