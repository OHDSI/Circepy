from __future__ import annotations

import ibis

from ..errors import UnsupportedFeatureError
from ..ibis.compiler import compile_event_plan
from ..ibis.context import ExecutionContext
from ..lower.criteria import lower_criterion
from ..normalize.groups import (
    NormalizedCorrelatedCriteria,
    NormalizedCriteriaGroup,
)
from ..normalize.windows import NormalizedWindow, NormalizedWindowBound


def _union_all(tables):
    current = tables[0]
    for table in tables[1:]:
        current = current.union(table, distinct=False)
    return current


def _event_keys(events):
    return events.select(
        events.person_id.cast("int64").name("person_id"),
        events.event_id.cast("int64").name("event_id"),
    ).distinct()


def _attach_observation_period(events, ctx: ExecutionContext):
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
        events.person_id.name("person_id"),
        events.event_id.name("event_id"),
        events.start_date.name("start_date"),
        events.end_date.name("end_date"),
        events.visit_occurrence_id.name("visit_occurrence_id"),
        observation_period.observation_period_start_date.cast("date").name("op_start_date"),
        observation_period.observation_period_end_date.cast("date").name("op_end_date"),
    ).distinct()


def _window_bound_expression(
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


def _apply_window_constraints(joined, correlated: NormalizedCorrelatedCriteria):
    predicate = joined.a_person_id == joined.p_person_id

    if not correlated.ignore_observation_period:
        predicate = predicate & (joined.a_start_date >= joined.p_op_start_date)
        predicate = predicate & (joined.a_start_date <= joined.p_op_end_date)

    start_window: NormalizedWindow | None = correlated.start_window
    if start_window is not None:
        start_index_anchor = (
            joined.p_end_date if bool(start_window.use_index_end) else joined.p_start_date
        )
        # Java semantics: use_event_end only when explicitly true.
        start_event_date = (
            joined.a_end_date
            if (start_window.use_event_end is not None and start_window.use_event_end)
            else joined.a_start_date
        )

        start_lower = _window_bound_expression(
            start_window.start,
            index_anchor_expr=start_index_anchor,
            use_observation_period=(not correlated.ignore_observation_period),
            op_start_expr=joined.p_op_start_date,
            op_end_expr=joined.p_op_end_date,
        )
        if start_lower is not None:
            predicate = predicate & (start_event_date >= start_lower)

        start_upper = _window_bound_expression(
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
        end_index_anchor = (
            joined.p_end_date if bool(end_window.use_index_end) else joined.p_start_date
        )
        # Java semantics: use_event_end defaults to true for end window when null.
        end_event_date = (
            joined.a_end_date
            if (end_window.use_event_end is None or end_window.use_event_end)
            else joined.a_start_date
        )

        end_lower = _window_bound_expression(
            end_window.start,
            index_anchor_expr=end_index_anchor,
            use_observation_period=(not correlated.ignore_observation_period),
            op_start_expr=joined.p_op_start_date,
            op_end_expr=joined.p_op_end_date,
        )
        if end_lower is not None:
            predicate = predicate & (end_event_date >= end_lower)

        end_upper = _window_bound_expression(
            end_window.end,
            index_anchor_expr=end_index_anchor,
            use_observation_period=(not correlated.ignore_observation_period),
            op_start_expr=joined.p_op_start_date,
            op_end_expr=joined.p_op_end_date,
        )
        if end_upper is not None:
            predicate = predicate & (end_event_date <= end_upper)

    if correlated.restrict_visit:
        predicate = predicate & (
            joined.a_visit_occurrence_id == joined.p_visit_occurrence_id
        )

    return joined.filter(predicate)


def _resolve_distinct_count_column(count_column: str | None) -> str:
    if count_column is None:
        return "a_concept_id"

    normalized = count_column.lower()
    mapping = {
        "domain_concept_id": "a_concept_id",
        "domain_source_concept_id": "a_source_concept_id",
        "visit_occurrence_id": "a_visit_occurrence_id",
        "visit_id": "a_visit_occurrence_id",
        "start_date": "a_start_date",
        "end_date": "a_end_date",
    }
    if normalized in mapping:
        return mapping[normalized]

    raise UnsupportedFeatureError(
        f"Unsupported distinct count column for correlated criteria: {count_column}"
    )


def _occurrence_predicate(match_count_expr, occurrence_type: int, occurrence_count: int):
    if occurrence_type == 0:
        return match_count_expr == occurrence_count
    if occurrence_type == 1:
        return match_count_expr <= occurrence_count
    if occurrence_type == 2:
        return match_count_expr >= occurrence_count
    raise UnsupportedFeatureError(
        f"Unsupported occurrence type for correlated criteria: {occurrence_type}"
    )


def _group_predicate(match_count_expr, mode: str, count: int | None, child_count: int):
    normalized_mode = (mode or "ALL").upper()
    if normalized_mode == "ALL":
        return match_count_expr == child_count
    if normalized_mode == "ANY":
        return match_count_expr > 0
    if normalized_mode == "AT_LEAST":
        threshold = 0 if count is None else int(count)
        return match_count_expr >= threshold
    if normalized_mode == "AT_MOST":
        threshold = 0 if count is None else int(count)
        return match_count_expr <= threshold
    raise UnsupportedFeatureError(
        f"Unsupported criteria group mode in Ibis executor: {mode}"
    )


def _compile_correlated_events(
    correlated: NormalizedCorrelatedCriteria,
    *,
    criterion_index: int,
    ctx: ExecutionContext,
):
    event_plan = lower_criterion(correlated.criterion, criterion_index=criterion_index)
    return compile_event_plan(event_plan, ctx)


def _correlated_match_keys(
    index_events,
    correlated: NormalizedCorrelatedCriteria,
    *,
    criterion_index: int,
    ctx: ExecutionContext,
):
    correlated_events = _compile_correlated_events(
        correlated,
        criterion_index=criterion_index,
        ctx=ctx,
    )

    p = index_events.select(
        index_events.person_id.name("p_person_id"),
        index_events.event_id.name("p_event_id"),
        index_events.start_date.name("p_start_date"),
        index_events.end_date.name("p_end_date"),
        index_events.visit_occurrence_id.name("p_visit_occurrence_id"),
        index_events.op_start_date.name("p_op_start_date"),
        index_events.op_end_date.name("p_op_end_date"),
    )
    a = correlated_events.select(
        correlated_events.person_id.name("a_person_id"),
        correlated_events.event_id.name("a_event_id"),
        correlated_events.start_date.name("a_start_date"),
        correlated_events.end_date.name("a_end_date"),
        correlated_events.visit_occurrence_id.name("a_visit_occurrence_id"),
        correlated_events.concept_id.name("a_concept_id"),
        correlated_events.source_concept_id.name("a_source_concept_id"),
    )

    joined = p.join(a, p.p_person_id == a.a_person_id)
    constrained = _apply_window_constraints(joined, correlated)

    if correlated.occurrence_is_distinct:
        distinct_col = _resolve_distinct_count_column(correlated.occurrence_count_column)
        counts = constrained.group_by(
            constrained.p_person_id,
            constrained.p_event_id,
        ).aggregate(match_count=constrained[distinct_col].nunique())
    else:
        counts = constrained.group_by(
            constrained.p_person_id,
            constrained.p_event_id,
        ).aggregate(match_count=constrained.a_event_id.count())

    keys = _event_keys(index_events)
    joined_counts = keys.left_join(
        counts,
        (keys.person_id == counts.p_person_id) & (keys.event_id == counts.p_event_id),
    )
    counted = joined_counts.mutate(
        match_count=ibis.coalesce(joined_counts.match_count, ibis.literal(0))
    )

    predicate = _occurrence_predicate(
        counted.match_count,
        int(correlated.occurrence_type),
        int(correlated.occurrence_count),
    )
    return counted.filter(predicate).select(
        counted.person_id.name("person_id"),
        counted.event_id.name("event_id"),
    )


def _evaluate_group(index_events, group: NormalizedCriteriaGroup, ctx: ExecutionContext):
    keys = _event_keys(index_events)

    if group.is_empty():
        return keys

    if group.demographics:
        raise UnsupportedFeatureError(
            "Demographic criteria groups are not implemented in this execution phase."
        )

    child_results = []
    index_id = 0

    for correlated in group.criteria:
        correlated_matches = _correlated_match_keys(
            index_events,
            correlated,
            criterion_index=index_id,
            ctx=ctx,
        )
        child_results.append(
            correlated_matches.mutate(index_id=ibis.literal(index_id, type="int64"))
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

    unioned = _union_all(child_results)
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

    predicate = _group_predicate(
        counted.matched_children,
        group.mode,
        group.count,
        index_id,
    )
    return counted.filter(predicate).select(
        counted.person_id.name("person_id"),
        counted.event_id.name("event_id"),
    )


def apply_additional_criteria(events, group: NormalizedCriteriaGroup | None, ctx):
    if group is None or group.is_empty():
        return events

    index_events = _attach_observation_period(events, ctx)
    matched_keys = _evaluate_group(index_events, group, ctx)

    filtered = events.join(
        matched_keys,
        (events.person_id == matched_keys.person_id)
        & (events.event_id == matched_keys.event_id),
    )
    return filtered.select(*[filtered[c] for c in events.columns])
