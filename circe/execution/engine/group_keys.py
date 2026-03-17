from __future__ import annotations

from ..plan.schema import EVENT_ID, PERSON_ID
from ..typing import Table


def union_all(tables: list[Table]) -> Table:
    current = tables[0]
    for table in tables[1:]:
        current = current.union(table, distinct=False)
    return current


def event_keys(events: Table) -> Table:
    return events.select(
        events.person_id.cast("int64").name(PERSON_ID),
        events.event_id.cast("int64").name(EVENT_ID),
    ).distinct()
