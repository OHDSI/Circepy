from __future__ import annotations

import ibis
import ibis.common.exceptions as ibis_exc
import ibis.expr.types as ir
import polars as pl

from ...cohortdefinition import CohortExpression
from ..build_context import BuildContext
from .common import (
    apply_end_strategy,
    apply_observation_window,
    collapse_events,
    has_end_strategy,
)
from .groups import apply_criteria_group
from .post_processing import apply_censor_window, apply_censoring, apply_inclusion_rules
from .registry import build_events

OUTPUT_SCHEMA = {
    "person_id": pl.Int64,
    "event_id": pl.Int64,
    "start_date": pl.Datetime,
    "end_date": pl.Datetime,
    "visit_occurrence_id": pl.Int64,
}


def build_primary_events(expression: CohortExpression, ctx: BuildContext):
    def _maybe_materialize(table: ir.Table, label: str) -> ir.Table:
        return ctx.maybe_materialize(table, label=label, analyze=True)

    primary = expression.primary_criteria
    if primary is None or not primary.criteria_list:
        return None
    event_tables: list[ir.Table] = []
    for criteria in primary.criteria_list:
        table = build_events(criteria, ctx)
        if table is None:
            continue
        event_tables.append(table)
    if not event_tables:
        return None
    if ctx.should_materialize_stages():
        materialized: list[ir.Table] = []
        for idx, table in enumerate(event_tables, start=1):
            materialized.append(ctx.maybe_materialize(table, label=f"primary_src_{idx}", analyze=True))
        event_tables = materialized
    events = event_tables[0]
    for table in event_tables[1:]:
        events = events.union(table, distinct=False)
    events = events.mutate(_source_event_id=events.event_id)
    events = apply_observation_window(events, primary.observation_window, ctx)
    events = _assign_primary_event_ids(events)
    if _should_limit(primary.primary_limit):
        events = _apply_result_limit(events, primary.primary_limit)

    events = ctx.maybe_materialize(events, label="primary_events", analyze=True)

    # Short-circuit the remainder of the pipeline when no primary events exist.
    if ctx.should_materialize_stages():
        try:
            primary_count = events.count().execute()
        except (ibis_exc.IbisError, RuntimeError, ValueError, TypeError):
            primary_count = None
        if primary_count == 0:
            events = _drop_aux_columns(events)
            return events.limit(0)

    events = apply_criteria_group(events, expression.additional_criteria, ctx)
    if expression.additional_criteria:
        events = ctx.maybe_materialize(events, label="additional_criteria", analyze=True)

    events = apply_inclusion_rules(events, expression.inclusion_rules, ctx)
    if expression.inclusion_rules:
        events = ctx.maybe_materialize(events, label="inclusion", analyze=True)
    # Circe ignores QualifiedLimit, so we do the same to preserve parity.
    if _should_limit(expression.expression_limit):
        events = _apply_result_limit(events, expression.expression_limit)
    events = apply_end_strategy(events, expression.end_strategy, ctx)
    if has_end_strategy(expression.end_strategy):
        events = _maybe_materialize(events, label="strategy_ends")

    # Censoring should cut the cohort end date, so apply it after end strategy.
    events = apply_censoring(events, expression.censoring_criteria, ctx)
    if expression.censoring_criteria:
        events = ctx.maybe_materialize(events, label="censoring", analyze=True)
    events = apply_censor_window(events, expression.censor_window, ctx)
    events = _drop_aux_columns(events)
    events = collapse_events(events, expression.collapse_settings)
    if expression.collapse_settings and expression.collapse_settings.collapse_type:
        events = _maybe_materialize(events, label="final_cohort")
    return events


def build_primary_events_polars(expression: CohortExpression, ctx: BuildContext) -> pl.DataFrame:
    events = build_primary_events(expression, ctx)
    if events is None:
        return pl.DataFrame(schema=OUTPUT_SCHEMA)
    return events.to_polars()


def _assign_primary_event_ids(events):
    if "_source_event_id" not in events.columns:
        events = events.mutate(_source_event_id=events.event_id)
    order = [events.person_id, events.start_date, events._source_event_id]
    person_window = ibis.window(group_by=events.person_id, order_by=order[1:])
    person_rank = ibis.row_number().over(person_window)
    events = events.mutate(
        # Keep event ids unique *within* a person to avoid global sorts/shuffles.
        # Most downstream logic keys by (person_id, event_id).
        event_id=(person_rank + 1),
        _person_ordinal=(person_rank + 1),
    )
    supplemental = [events[column] for column in ("observation_period_start_date", "observation_period_end_date") if column in events.columns]
    return events.select(
        events.person_id,
        events.event_id,
        events.start_date,
        events.end_date,
        events.visit_occurrence_id,
        events._source_event_id,
        events._person_ordinal,
        *supplemental,
    )


def _apply_result_limit(events: ir.Table, limit) -> ir.Table:
    if not limit or (limit.type or "ALL").lower() == "all":
        return events

    order_by = [events.start_date]
    if "event_id" in events.columns:
        order_by.append(events.event_id)

    w = ibis.window(group_by=events.person_id, order_by=order_by)

    helper = "__mitos_rn__"

    ranked = events.mutate(**{helper: ibis.row_number().over(w)})
    limited = ranked.filter(ranked[helper] == 0)

    return limited.select([limited[c] for c in events.columns])


def _drop_aux_columns(events: ir.Table) -> ir.Table:
    drop_cols = [
        col
        for col in (
            "_source_event_id",
            "_person_ordinal",
            "observation_period_start_date",
            "observation_period_end_date",
            "_result_row",
        )
        if col in events.columns
    ]
    if drop_cols:
        events = events.drop(*drop_cols)
    return events


def _should_limit(limit) -> bool:
    return bool(limit and (limit.type or "all").lower() != "all")
