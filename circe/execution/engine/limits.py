from __future__ import annotations

import ibis

from ..plan.schema import DOMAIN, EVENT_ID, PERSON_ID, START_DATE


def apply_result_limit(events, limit_type: str):
    normalized = (limit_type or "all").lower()
    if normalized in {"all", ""}:
        return events

    descending = normalized == "last"
    order_by = [events[START_DATE], events[EVENT_ID]]
    if DOMAIN in events.columns:
        order_by.append(events[DOMAIN])

    if descending:
        order_by = [expr.desc() for expr in order_by]

    window = ibis.window(
        group_by=events[PERSON_ID],
        order_by=order_by,
    )
    ranked = events.mutate(_limit_rn=ibis.row_number().over(window))
    return ranked.filter(ranked._limit_rn == 0).drop("_limit_rn")
