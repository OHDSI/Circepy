from __future__ import annotations

import ibis

from ..ibis.context import ExecutionContext
from ..normalize.groups import NormalizedCriteriaGroup
from ..plan.schema import EVENT_ID, PERSON_ID
from ..typing import Table
from .group_demographics import demographic_match_keys
from .group_keys import event_keys, union_all
from .group_operators import correlated_match_keys, group_predicate
from .group_windows import attach_observation_period


def _evaluate_group(
    index_events: Table,
    group: NormalizedCriteriaGroup,
    ctx: ExecutionContext,
) -> Table:
    keys = event_keys(index_events)

    if group.is_empty():
        return keys

    child_results: list[Table] = []
    index_id = 0

    for correlated in group.criteria:
        correlated_matches = correlated_match_keys(
            index_events,
            correlated,
            criterion_index=index_id,
            ctx=ctx,
        )
        child_results.append(
            correlated_matches.mutate(index_id=ibis.literal(index_id, type="int64"))
        )
        index_id += 1

    for demographic in group.demographics:
        demographic_matches = demographic_match_keys(index_events, demographic, ctx)
        child_results.append(
            demographic_matches.mutate(index_id=ibis.literal(index_id, type="int64"))
        )
        index_id += 1

    for child_group in group.groups:
        child_group_matches = _evaluate_group(index_events, child_group, ctx)
        child_results.append(
            child_group_matches.mutate(index_id=ibis.literal(index_id, type="int64"))
        )
        index_id += 1

    if not child_results:
        return keys

    unioned = union_all(child_results)
    group_counts = unioned.group_by(unioned.person_id, unioned.event_id).aggregate(
        matched_children=unioned.index_id.nunique()
    )

    joined_counts = keys.left_join(
        group_counts,
        (keys.person_id == group_counts.person_id)
        & (keys.event_id == group_counts.event_id),
    )
    counted = joined_counts.mutate(
        matched_children=ibis.coalesce(joined_counts.matched_children, ibis.literal(0))
    )

    predicate = group_predicate(
        counted.matched_children,
        group.mode,
        group.count,
        index_id,
    )
    return counted.filter(predicate).select(
        counted.person_id.name(PERSON_ID),
        counted.event_id.name(EVENT_ID),
    )


def apply_additional_criteria(
    events: Table,
    group: NormalizedCriteriaGroup | None,
    ctx: ExecutionContext,
) -> Table:
    if group is None or group.is_empty():
        return events

    index_events = attach_observation_period(events, ctx)
    matched_keys = _evaluate_group(index_events, group, ctx)

    filtered = events.join(
        matched_keys,
        (events.person_id == matched_keys.person_id)
        & (events.event_id == matched_keys.event_id),
    )
    return filtered.select(*[filtered[c] for c in events.columns])
