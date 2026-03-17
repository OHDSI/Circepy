from __future__ import annotations

import ibis

from ..errors import UnsupportedFeatureError
from ..ibis.compiler import compile_event_plan
from ..ibis.context import ExecutionContext
from ..lower.criteria import lower_criterion
from ..normalize.groups import NormalizedCorrelatedCriteria
from ..plan.schema import (
    CONCEPT_ID,
    DAYS_SUPPLY,
    DURATION,
    END_DATE,
    EVENT_ID,
    GAP_DAYS,
    OCCURRENCE_COUNT,
    PERSON_ID,
    QUANTITY,
    RANGE_HIGH,
    RANGE_LOW,
    REFILLS,
    SOURCE_CONCEPT_ID,
    START_DATE,
    UNIT_CONCEPT_ID,
    VALUE_AS_NUMBER,
    VISIT_DETAIL_ID,
    VISIT_OCCURRENCE_ID,
)
from ..typing import Table
from .group_keys import event_keys
from .group_windows import apply_window_constraints


def resolve_distinct_count_column(count_column: str | None) -> str:
    if count_column is None:
        return f"a_{CONCEPT_ID}"

    normalized = count_column.lower()
    mapping = {
        "domain_concept_id": f"a_{CONCEPT_ID}",
        "domain_source_concept_id": f"a_{SOURCE_CONCEPT_ID}",
        VISIT_OCCURRENCE_ID: f"a_{VISIT_OCCURRENCE_ID}",
        "visit_id": f"a_{VISIT_OCCURRENCE_ID}",
        "visit_detail_id": f"a_{VISIT_DETAIL_ID}",
        START_DATE: f"a_{START_DATE}",
        END_DATE: f"a_{END_DATE}",
        "duration": f"a_{DURATION}",
        "quantity": f"a_{QUANTITY}",
        "days_supply": f"a_{DAYS_SUPPLY}",
        "refills": f"a_{REFILLS}",
        "range_low": f"a_{RANGE_LOW}",
        "range_high": f"a_{RANGE_HIGH}",
        "value_as_number": f"a_{VALUE_AS_NUMBER}",
        "unit_concept_id": f"a_{UNIT_CONCEPT_ID}",
        "occurrence_count": f"a_{OCCURRENCE_COUNT}",
        "gap_days": f"a_{GAP_DAYS}",
    }
    if normalized in mapping:
        return mapping[normalized]

    raise UnsupportedFeatureError(
        "Ibis executor group evaluation error: unsupported distinct count column "
        f"{count_column!r} for correlated criteria."
    )


def occurrence_predicate(match_count_expr, occurrence_type: int, occurrence_count: int):
    if occurrence_type == 0:
        return match_count_expr == occurrence_count
    if occurrence_type == 1:
        return match_count_expr <= occurrence_count
    if occurrence_type == 2:
        return match_count_expr >= occurrence_count
    raise UnsupportedFeatureError(
        f"Ibis executor group evaluation error: unsupported correlated occurrence type {occurrence_type}."
    )


def group_predicate(match_count_expr, mode: str, count: int | None, child_count: int):
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
        f"Ibis executor group evaluation error: unsupported criteria group mode {mode!r}."
    )


def _compile_correlated_events(
    correlated: NormalizedCorrelatedCriteria,
    *,
    criterion_index: int,
    ctx: ExecutionContext,
) -> Table:
    event_plan = lower_criterion(correlated.criterion, criterion_index=criterion_index)
    return compile_event_plan(event_plan, ctx)


def correlated_match_keys(
    index_events: Table,
    correlated: NormalizedCorrelatedCriteria,
    *,
    criterion_index: int,
    ctx: ExecutionContext,
) -> Table:
    correlated_events = _compile_correlated_events(
        correlated,
        criterion_index=criterion_index,
        ctx=ctx,
    )

    p = index_events.select(
        index_events[PERSON_ID].name("p_person_id"),
        index_events[EVENT_ID].name("p_event_id"),
        index_events[START_DATE].name("p_start_date"),
        index_events[END_DATE].name("p_end_date"),
        index_events[VISIT_OCCURRENCE_ID].name("p_visit_occurrence_id"),
        index_events.op_start_date.name("p_op_start_date"),
        index_events.op_end_date.name("p_op_end_date"),
    )
    a = correlated_events.select(
        correlated_events[PERSON_ID].name("a_person_id"),
        correlated_events[EVENT_ID].name("a_event_id"),
        correlated_events[START_DATE].name("a_start_date"),
        correlated_events[END_DATE].name("a_end_date"),
        correlated_events[VISIT_OCCURRENCE_ID].name("a_visit_occurrence_id"),
        correlated_events[VISIT_DETAIL_ID].name("a_visit_detail_id"),
        correlated_events[CONCEPT_ID].name("a_concept_id"),
        correlated_events[SOURCE_CONCEPT_ID].name("a_source_concept_id"),
        correlated_events[QUANTITY].name("a_quantity"),
        correlated_events[DAYS_SUPPLY].name("a_days_supply"),
        correlated_events[REFILLS].name("a_refills"),
        correlated_events[RANGE_LOW].name("a_range_low"),
        correlated_events[RANGE_HIGH].name("a_range_high"),
        correlated_events[VALUE_AS_NUMBER].name("a_value_as_number"),
        correlated_events[UNIT_CONCEPT_ID].name("a_unit_concept_id"),
        correlated_events[OCCURRENCE_COUNT].name("a_occurrence_count"),
        correlated_events[GAP_DAYS].name("a_gap_days"),
        correlated_events[DURATION].name("a_duration"),
    )

    joined = p.join(
        a,
        predicates=[p.p_person_id == a.a_person_id],
    )
    constrained = apply_window_constraints(joined, correlated)

    if correlated.occurrence_is_distinct:
        distinct_col = resolve_distinct_count_column(correlated.occurrence_count_column)
        counts = constrained.group_by(
            constrained.p_person_id,
            constrained.p_event_id,
        ).aggregate(match_count=constrained[distinct_col].nunique())
    else:
        counts = constrained.group_by(
            constrained.p_person_id,
            constrained.p_event_id,
        ).aggregate(match_count=constrained.a_event_id.count())

    keys = event_keys(index_events)
    joined_counts = keys.left_join(
        counts,
        predicates=[(keys.person_id == counts.p_person_id) & (keys.event_id == counts.p_event_id)],
    )
    counted = joined_counts.mutate(match_count=ibis.coalesce(joined_counts.match_count, ibis.literal(0)))

    predicate = occurrence_predicate(
        counted.match_count,
        int(correlated.occurrence_type),
        int(correlated.occurrence_count),
    )
    return counted.filter(predicate).select(
        counted.person_id.name(PERSON_ID),
        counted.event_id.name(EVENT_ID),
    )
