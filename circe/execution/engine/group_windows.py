from __future__ import annotations

import ibis

from ..ibis.context import ExecutionContext
from ..normalize.groups import NormalizedCorrelatedCriteria
from ..normalize.windows import NormalizedWindow, NormalizedWindowBound
from ..plan.schema import END_DATE, EVENT_ID, PERSON_ID, START_DATE, VISIT_OCCURRENCE_ID
from ..typing import Table


def attach_observation_period(events: Table, ctx: ExecutionContext) -> Table:
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
        events[PERSON_ID].name(PERSON_ID),
        events[EVENT_ID].name(EVENT_ID),
        events[START_DATE].name(START_DATE),
        events[END_DATE].name(END_DATE),
        events[VISIT_OCCURRENCE_ID].name(VISIT_OCCURRENCE_ID),
        observation_period.observation_period_start_date.cast("date").name("op_start_date"),
        observation_period.observation_period_end_date.cast("date").name("op_end_date"),
    ).distinct()


def window_bound_expression(
    bound: NormalizedWindowBound | None,
    *,
    index_anchor_expr,
    use_observation_period: bool,
    op_start_expr,
    op_end_expr,
):
    if bound is None:
        return None

    if bound.days is not None:
        return index_anchor_expr + ibis.interval(days=int(bound.coeff) * int(bound.days))

    if not use_observation_period:
        return None

    return op_start_expr if int(bound.coeff) == -1 else op_end_expr


def apply_window_constraints(joined, correlated: NormalizedCorrelatedCriteria):
    predicate = joined.a_person_id == joined.p_person_id

    if not correlated.ignore_observation_period:
        predicate = predicate & (joined.a_start_date >= joined.p_op_start_date)
        predicate = predicate & (joined.a_start_date <= joined.p_op_end_date)

    start_window: NormalizedWindow | None = correlated.start_window
    if start_window is not None:
        start_index_anchor = joined.p_end_date if bool(start_window.use_index_end) else joined.p_start_date
        start_event_date = (
            joined.a_end_date
            if (start_window.use_event_end is not None and start_window.use_event_end)
            else joined.a_start_date
        )

        start_lower = window_bound_expression(
            start_window.start,
            index_anchor_expr=start_index_anchor,
            use_observation_period=(not correlated.ignore_observation_period),
            op_start_expr=joined.p_op_start_date,
            op_end_expr=joined.p_op_end_date,
        )
        if start_lower is not None:
            predicate = predicate & (start_event_date >= start_lower)

        start_upper = window_bound_expression(
            start_window.end,
            index_anchor_expr=start_index_anchor,
            use_observation_period=(not correlated.ignore_observation_period),
            op_start_expr=joined.p_op_start_date,
            op_end_expr=joined.p_op_end_date,
        )
        if start_upper is not None:
            predicate = predicate & (start_event_date <= start_upper)

    end_window: NormalizedWindow | None = correlated.end_window
    if end_window is not None:
        end_index_anchor = joined.p_end_date if bool(end_window.use_index_end) else joined.p_start_date
        end_event_date = (
            joined.a_end_date
            if (end_window.use_event_end is None or end_window.use_event_end)
            else joined.a_start_date
        )

        end_lower = window_bound_expression(
            end_window.start,
            index_anchor_expr=end_index_anchor,
            use_observation_period=(not correlated.ignore_observation_period),
            op_start_expr=joined.p_op_start_date,
            op_end_expr=joined.p_op_end_date,
        )
        if end_lower is not None:
            predicate = predicate & (end_event_date >= end_lower)

        end_upper = window_bound_expression(
            end_window.end,
            index_anchor_expr=end_index_anchor,
            use_observation_period=(not correlated.ignore_observation_period),
            op_start_expr=joined.p_op_start_date,
            op_end_expr=joined.p_op_end_date,
        )
        if end_upper is not None:
            predicate = predicate & (end_event_date <= end_upper)

    if correlated.restrict_visit:
        predicate = predicate & (joined.a_visit_occurrence_id == joined.p_visit_occurrence_id)

    return joined.filter(predicate)
