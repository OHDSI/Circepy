from __future__ import annotations

import ibis

from ..evaluation.models import EvaluationRubric
from .engine.group_windows import attach_observation_period
from .engine.groups import _evaluate_group
from .ibis.context import ExecutionContext
from .normalize.groups import normalize_criteria_group
from .typing import Table


def build_evaluation(
    rubric: EvaluationRubric,
    index_events: Table,
    ctx: ExecutionContext,
    ruleset_id: int,
    include_cohort_id: bool = True,
) -> Table:
    """
    Translates an EvaluationRubric into an Ibis Table expression natively.

    The resulting table has columns:
    - ruleset_id: int
    - cohort_definition_id: int (if include_cohort_id and present in index_events)
    - subject_id: int (mapped from person_id)
    - index_date: date (mapped from start_date)
    - rule_id: int
    - score: float
    """

    # 1. Ensure the index_events have observation periods attached for time_window rules
    # Standard query building attaches this as op_start_date, op_end_date
    events_with_op = attach_observation_period(index_events, ctx)

    rule_results = []

    for rule in rubric.rules:
        # 2. Normalize criteria group
        normalized_group = normalize_criteria_group(rule.expression)
        if normalized_group is None or normalized_group.is_empty():
            continue

        # 3. Evaluate criteria group against index events
        # _evaluate_group returns a table with keys: person_id, event_id
        matched_keys = _evaluate_group(events_with_op, normalized_group, ctx)

        # 4. Join matches back to index_events to get start_date (index_date)
        # We need subject_id, index_date from the original events
        matched_events = events_with_op.join(
            matched_keys,
            predicates=[
                (events_with_op.person_id == matched_keys.person_id)
                & (events_with_op.event_id == matched_keys.event_id)
            ],
            how="inner",
        )

        score_val = float(rule.weight * rule.polarity)

        # 5. Project required columns
        columns = [
            ibis.literal(ruleset_id, type="int").name("ruleset_id"),
        ]

        if include_cohort_id:
            if "cohort_definition_id" in matched_events.columns:
                columns.append(matched_events.cohort_definition_id.name("cohort_definition_id"))
            else:
                # If cohort_definition_id is not in index_events, fallback to 0 or leave it out?
                # A proper OHDSI cohort table has cohort_definition_id.
                columns.append(ibis.literal(0, type="int64").name("cohort_definition_id"))

        columns.extend(
            [
                matched_events.person_id.name("subject_id"),
                matched_events.start_date.cast("date").name("index_date"),
                ibis.literal(rule.rule_id, type="int").name("rule_id"),
                ibis.literal(score_val, type="float64").name("score"),
            ]
        )

        # Need distinct results (similar to SELECT DISTINCT in the SQL translation)
        rule_table = matched_events.select(*columns).distinct()
        rule_results.append(rule_table)

    if not rule_results:
        # Return an empty schema if no rules are available
        empty_cols = [
            ("ruleset_id", "int"),
        ]
        if include_cohort_id:
            empty_cols.append(("cohort_definition_id", "int64"))
        empty_cols.extend(
            [
                ("subject_id", "int64"),
                ("index_date", "date"),
                ("rule_id", "int"),
                ("score", "float64"),
            ]
        )
        return ibis.memtable([], schema=ibis.schema(empty_cols))

    # 6. Union all rule results
    if len(rule_results) == 1:
        return rule_results[0]

    return ibis.union(*rule_results)
