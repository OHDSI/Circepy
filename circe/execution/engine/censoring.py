from __future__ import annotations

import ibis

from ..ibis.compiler import compile_event_plan
from ..lower.criteria import lower_criterion
from .end_strategy import attach_observation_bounds


def _union_all(tables):
    current = tables[0]
    for table in tables[1:]:
        current = current.union(table, distinct=False)
    return current


def _compile_censor_events(criteria, ctx):
    compiled = []
    for index, criterion in enumerate(criteria):
        plan = lower_criterion(criterion, criterion_index=10_000 + index)
        table = compile_event_plan(plan, ctx)
        compiled.append(
            table.select(
                table.person_id.cast("int64").name("person_id"),
                table.start_date.cast("date").name("censor_start_date"),
            )
        )
    if not compiled:
        return None
    return _union_all(compiled)


def apply_censoring(events, criteria, window, ctx):
    del window  # Censor-window clipping is applied in collapse/finalization stage.

    if not criteria:
        return events

    censor_events = _compile_censor_events(criteria, ctx)
    with_bounds = attach_observation_bounds(events, ctx)

    joined = with_bounds.join(
        censor_events,
        with_bounds.person_id == censor_events.person_id,
    )
    valid = joined.filter(
        (joined.censor_start_date >= joined.start_date)
        & (joined.censor_start_date <= joined.op_end_date)
    )
    censor_min = valid.group_by(valid.person_id, valid.event_id).aggregate(
        censor_end_date=valid.censor_start_date.min()
    )

    merged = with_bounds.left_join(
        censor_min,
        (with_bounds.person_id == censor_min.person_id)
        & (with_bounds.event_id == censor_min.event_id),
    )

    new_end = ibis.coalesce(
        ibis.least(merged.end_date, merged.censor_end_date),
        merged.end_date,
    )
    projected = merged.mutate(_new_end_date=new_end)

    return projected.select(
        *[
            projected[c]
            if c != "end_date"
            else projected._new_end_date.cast("date").name("end_date")
            for c in events.columns
        ]
    )
