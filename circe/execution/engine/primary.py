from __future__ import annotations

import ibis

from ..errors import ExecutionNormalizationError
from ..ibis.compiler import compile_event_plan
from ..ibis.context import ExecutionContext
from ..normalize.windows import NormalizedObservationWindow
from ..plan.cohort import CohortPlan
from ..plan.schema import DOMAIN, EVENT_ID, PERSON_ID, START_DATE
from ..typing import Table
from .groups import apply_additional_criteria
from .limits import apply_result_limit


def _union_all(tables):
    current = tables[0]
    for table in tables[1:]:
        current = current.union(table, distinct=False)
    return current


def _assign_primary_event_ids(events):
    ordering = [events[START_DATE], events[EVENT_ID], events[DOMAIN]]
    person_window = ibis.window(group_by=events[PERSON_ID], order_by=ordering)
    ranked = events.mutate(_primary_rn=ibis.row_number().over(person_window))
    return ranked.mutate(**{EVENT_ID: ranked._primary_rn + 1}).drop("_primary_rn")


def _apply_observation_window(
    events,
    ctx: ExecutionContext,
    window: NormalizedObservationWindow,
):
    observation_period = ctx.table("observation_period").select(
        PERSON_ID,
        "observation_period_start_date",
        "observation_period_end_date",
    )
    joined = events.join(
        observation_period,
        events[PERSON_ID] == observation_period[PERSON_ID],
    )
    lower = joined.observation_period_start_date + ibis.interval(days=window.prior_days)
    upper = joined.observation_period_end_date - ibis.interval(days=window.post_days)
    filtered = joined.filter((joined[START_DATE] >= lower) & (joined[START_DATE] <= upper))
    return filtered.select(*[filtered[c] for c in events.columns])


def build_primary_events(plan: CohortPlan, ctx: ExecutionContext) -> Table:
    if not plan.primary_event_plans:
        raise ExecutionNormalizationError(
            "Ibis executor primary build error: no primary criteria were lowered to executable plans."
        )

    compiled = []
    for primary in plan.primary_event_plans:
        events = compile_event_plan(primary.event_plan, ctx)
        events = apply_additional_criteria(events, primary.correlated_criteria, ctx)
        compiled.append(events)

    events = _union_all(compiled)
    events = _assign_primary_event_ids(events)

    if plan.observation_window is not None:
        events = _apply_observation_window(events, ctx, plan.observation_window)

    events = apply_result_limit(events, plan.primary_limit_type)
    return events
