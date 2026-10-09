from __future__ import annotations

from ..plan.schema import EVENT_ID, PERSON_ID
from ..typing import Table


def _binary_union(tables: list[Table]) -> Table:
    if len(tables) == 1:
        return tables[0]
    mid = len(tables) // 2
    left = _binary_union(tables[:mid])
    right = _binary_union(tables[mid:])
    return left.union(right, distinct=False)


def union_all(tables: list[Table]) -> Table:
    return _binary_union(tables)


def event_keys(events: Table) -> Table:
    return events.select(
        events.person_id.cast("int64").name(PERSON_ID),
        events.event_id.cast("int64").name(EVENT_ID),
    ).distinct()
