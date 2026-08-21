from __future__ import annotations

import ibis

from ..ibis.context import ExecutionContext
from ..normalize.groups import NormalizedCriteriaGroup
from ..plan.schema import EVENT_ID, OP_END_DATE, OP_START_DATE, PERSON_ID
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

    child_matches: list[Table] = []

    for index_id, correlated in enumerate(group.criteria):
        child_matches.append(
            correlated_match_keys(
                index_events,
                correlated,
                criterion_index=index_id,
                ctx=ctx,
            )
        )

    index_id = len(child_matches)

    for demographic in group.demographics:
        child_matches.append(demographic_match_keys(index_events, demographic, ctx))
        index_id += 1

    for child_group in group.groups:
        child_matches.append(_evaluate_group(index_events, child_group, ctx))
        index_id += 1

    if not child_matches:
        return keys

    normalized_mode = (group.mode or "ALL").upper()
    if normalized_mode == "ANY":
        return union_all(child_matches).distinct()

    if normalized_mode == "AT_LEAST" and group.count is not None and int(group.count) <= 1:
        return union_all(child_matches).distinct()

    if len(child_matches) == 1 and normalized_mode == "ALL":
        return child_matches[0]

    child_results: list[Table] = []
    for index_id, child_match in enumerate(child_matches):
        child_results.append(child_match.mutate(index_id=ibis.literal(index_id, type="int64")))

    unioned = union_all(child_results)
    group_counts = unioned.group_by(unioned.person_id, unioned.event_id).aggregate(
        matched_children=unioned.index_id.nunique()
    )

    joined_counts = keys.left_join(
        group_counts,
        predicates=[(keys.person_id == group_counts.person_id) & (keys.event_id == group_counts.event_id)],
    )
    counted = joined_counts.mutate(
        matched_children=ibis.coalesce(joined_counts.matched_children, ibis.literal(0))
    )

    predicate = group_predicate(
        counted.matched_children,
        group.mode,
        group.count,
        len(child_matches),
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

    # Use pre-existing OP bounds from primary events if available,
    # avoiding a re-join that creates duplicates when overlapping OPs exist.
    if OP_START_DATE in events.columns and OP_END_DATE in events.columns:
        index_events = events
    else:
        index_events = attach_observation_period(events, ctx)
    matched_keys = _evaluate_group(index_events, group, ctx)

    filtered = events.join(
        matched_keys,
        predicates=[
            (events.person_id == matched_keys.person_id) & (events.event_id == matched_keys.event_id)
        ],
    )
    return filtered.select(*[filtered[c] for c in events.columns])
