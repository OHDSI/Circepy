from __future__ import annotations

import contextlib

from ..ibis.context import ExecutionContext
from ..ibis.operations import create_table, read_table
from ..lower.criteria import lower_criterion
from ..normalize.cohort import NormalizedCohort
from ..plan.cohort import CohortPlan, PrimaryEventInput
from ..typing import Table
from .censoring import apply_censoring
from .collapse import collapse_events
from .end_strategy import apply_end_strategy
from .groups import apply_additional_criteria
from .inclusion import apply_inclusion_rules
from .limits import apply_result_limit
from .primary import build_primary_events


def _materialize(
    table: Table,
    *,
    ctx: ExecutionContext,
    cohort_id: int,
    stage: str,
    schema: str | None,
) -> Table:
    """Write *table* to a backend staging table and return a fresh reference.

    Without this step every pipeline stage accumulates on top of the previous
    ibis expression tree.  For cohorts with many primary criteria the tree
    grows too large for the ibis SQL compiler to traverse in reasonable time.

    Materialising at each pipeline boundary keeps the expression tree sent
    to the compiler shallow — each stage only builds on a simple
    ``DatabaseTable`` reference.
    """
    name = f"__cg_{cohort_id}_{stage}"
    create_table(ctx.backend, table_name=name, schema=schema, obj=table, overwrite=True)
    return read_table(ctx.backend, table_name=name, schema=schema)


def _drop_staging_tables(
    ctx: ExecutionContext,
    cohort_id: int,
    schema: str | None,
) -> None:
    """Remove all staging tables for *cohort_id* from the database."""
    for stage in ("primary", "qualified", "included", "ended"):
        name = f"__cg_{cohort_id}_{stage}"
        with contextlib.suppress(Exception):
            ctx.backend.drop_table(name, database=schema, force=True)


def build_cohort_table(
    normalized: NormalizedCohort,
    ctx: ExecutionContext,
    *,
    cohort_id: int = 0,
    materialize: bool = True,
) -> Table:
    primary_plans = tuple(
        PrimaryEventInput(
            event_plan=lower_criterion(criterion, criterion_index=index),
            correlated_criteria=criterion.correlated_criteria,
        )
        for index, criterion in enumerate(normalized.primary.criteria)
    )
    cohort_plan = CohortPlan(
        primary_event_plans=primary_plans,
        observation_window=normalized.primary.observation_window,
        primary_limit_type=normalized.primary.primary_limit_type,
        qualified_limit_type=normalized.result_limits.qualified_limit_type,
        expression_limit_type=normalized.result_limits.expression_limit_type,
    )

    schema = ctx.results_schema or ctx.cdm_schema

    # ── Primary events ──────────────────────────────────────────────────
    primary_events = build_primary_events(cohort_plan, ctx)
    if materialize:
        primary_events = _materialize(
            primary_events, ctx=ctx, cohort_id=cohort_id, stage="primary", schema=schema
        )

    # ── Additional (correlated) criteria ────────────────────────────────
    qualified_events = apply_additional_criteria(primary_events, normalized.additional_criteria, ctx)
    if normalized.additional_criteria is not None and not normalized.additional_criteria.is_empty():
        qualified_events = apply_result_limit(qualified_events, cohort_plan.qualified_limit_type)
    if materialize:
        qualified_events = _materialize(
            qualified_events, ctx=ctx, cohort_id=cohort_id, stage="qualified", schema=schema
        )

    # ── Inclusion rules ─────────────────────────────────────────────────
    # Materialise after every inclusion rule so that the ibis expression tree
    # never grows deeper than one rule's worth of operations.  Without this a
    # cohort with N rules builds an N-level tree that, when compiled into a
    # single SQL statement, produces query plans too large for some backends
    # (e.g. Databricks Spark) to execute without resource exhaustion.
    if materialize and normalized.inclusion_rules:
        included_events = qualified_events
        for rule in normalized.inclusion_rules:
            included_events = apply_additional_criteria(included_events, rule.expression, ctx)
            included_events = _materialize(
                included_events, ctx=ctx, cohort_id=cohort_id, stage="included", schema=schema
            )
        included_events = apply_result_limit(included_events, cohort_plan.expression_limit_type)
    else:
        included_events = apply_inclusion_rules(qualified_events, normalized.inclusion_rules, ctx)
        included_events = apply_result_limit(included_events, cohort_plan.expression_limit_type)
        if materialize:
            included_events = _materialize(
                included_events, ctx=ctx, cohort_id=cohort_id, stage="included", schema=schema
            )

    # ── End strategy ────────────────────────────────────────────────────
    ended_events = apply_end_strategy(included_events, normalized.end_strategy, ctx)
    if materialize:
        ended_events = _materialize(ended_events, ctx=ctx, cohort_id=cohort_id, stage="ended", schema=schema)

    # ── Censoring + collapse (final stage — no materialize after) ──────
    censored_events = apply_censoring(
        ended_events, normalized.censoring_criteria, normalized.censor_window, ctx
    )
    return collapse_events(censored_events, normalized.collapse_settings, normalized.censor_window)
