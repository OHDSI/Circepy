from __future__ import annotations

import ibis

from ..plan.schema import END_DATE, PERSON_ID, START_DATE


def _apply_censor_window(events, censor_window):
    if censor_window is None:
        return events

    start_expr = events.start_date
    end_expr = events.end_date

    if censor_window.start_date:
        start_bound = ibis.literal(censor_window.start_date).cast("date")
        start_expr = ibis.greatest(events.start_date, start_bound)

    if censor_window.end_date:
        end_bound = ibis.literal(censor_window.end_date).cast("date")
        end_expr = ibis.least(events.end_date, end_bound)

    clipped = events.mutate(start_date=start_expr, end_date=end_expr)
    return clipped.filter(clipped.start_date <= clipped.end_date)


def _collapse_era(intervals, era_pad: int):
    padded = intervals.mutate(
        _padded_end_date=(intervals.end_date + ibis.interval(days=int(era_pad)))
    )

    ordering = [padded.start_date]
    ordered_window = ibis.window(group_by=padded.person_id, order_by=ordering)
    with_cummax = padded.mutate(_cummax_padded_end=padded._padded_end_date.max().over(ordered_window))
    with_prev = with_cummax.mutate(
        _prev_max_padded_end=with_cummax._cummax_padded_end.lag().over(ordered_window)
    )
    marked = with_prev.mutate(
        _is_new_group=ibis.ifelse(
            with_prev._prev_max_padded_end.isnull()
            | (with_prev._prev_max_padded_end < with_prev.start_date),
            ibis.literal(1, type="int64"),
            ibis.literal(0, type="int64"),
        )
    )

    group_index = marked._is_new_group.sum().over(ordered_window)
    grouped = marked.mutate(_group_idx=group_index)

    collapsed = grouped.group_by(grouped.person_id, grouped._group_idx).aggregate(
        start_date=grouped.start_date.min(),
        _max_padded_end=grouped._padded_end_date.max(),
    )
    return collapsed.select(
        collapsed.person_id.cast("int64").name(PERSON_ID),
        collapsed.start_date.cast("date").name(START_DATE),
        (
            collapsed._max_padded_end - ibis.interval(days=int(era_pad))
        ).cast("date").name(END_DATE),
    )


def collapse_events(events, collapse_settings, censor_window):
    if collapse_settings is None:
        return _apply_censor_window(events, censor_window)

    collapse_type = (collapse_settings.collapse_type or "era").lower()
    if collapse_type == "no_collapse":
        return _apply_censor_window(events, censor_window)

    intervals = events.select(
        events.person_id.cast("int64").name(PERSON_ID),
        events.start_date.cast("date").name(START_DATE),
        events.end_date.cast("date").name(END_DATE),
    )
    intervals = _apply_censor_window(intervals, censor_window)
    return _collapse_era(intervals, collapse_settings.era_pad)
