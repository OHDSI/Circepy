from __future__ import annotations

import ibis

from ..errors import ExecutionNormalizationError
from ..ibis.compiler import compile_event_plan
from ..ibis.context import ExecutionContext
from ..normalize.windows import NormalizedObservationWindow
from ..plan.cohort import CohortPlan
from .groups import apply_additional_criteria


def _union_all(tables):
    current = tables[0]
    for table in tables[1:]:
        current = current.union(table, distinct=False)
    return current


def _assign_primary_event_ids(events):
    ordering = [events.start_date, events.event_id, events.domain]
    person_window = ibis.window(group_by=events.person_id, order_by=ordering)
    ranked = events.mutate(_primary_rn=ibis.row_number().over(person_window))
    return ranked.mutate(event_id=(ranked._primary_rn + 1)).drop("_primary_rn")


def _apply_observation_window(
    events,
    ctx: ExecutionContext,
    window: NormalizedObservationWindow,
):
    observation_period = ctx.table("observation_period").select(
        "person_id",
        "observation_period_start_date",
        "observation_period_end_date",
    )
    joined = events.join(
        observation_period,
        events.person_id == observation_period.person_id,
    )
    lower = joined.observation_period_start_date + ibis.interval(days=window.prior_days)
    upper = joined.observation_period_end_date - ibis.interval(days=window.post_days)
    filtered = joined.filter((joined.start_date >= lower) & (joined.start_date <= upper))
    return filtered.select(*[filtered[c] for c in events.columns])


def _apply_primary_limit(events, primary_limit_type: str):
    if primary_limit_type in {"all", ""}:
        return events
    window = ibis.window(
        group_by=events.person_id,
        order_by=[events.start_date, events.event_id],
    )
    ranked = events.mutate(_limit_rn=ibis.row_number().over(window))
    return ranked.filter(ranked._limit_rn == 0).drop("_limit_rn")


def build_primary_events(plan: CohortPlan, ctx: ExecutionContext):
    if not plan.primary_event_plans:
        raise ExecutionNormalizationError("No primary criteria were lowered to plans.")

    compiled = []
    for primary in plan.primary_event_plans:
        events = compile_event_plan(primary.event_plan, ctx)
        events = apply_additional_criteria(events, primary.correlated_criteria, ctx)
        compiled.append(events)

    events = _union_all(compiled)
    events = _assign_primary_event_ids(events)

    if plan.observation_window is not None:
        events = _apply_observation_window(events, ctx, plan.observation_window)

    events = _apply_primary_limit(events, plan.primary_limit_type)
    return events
