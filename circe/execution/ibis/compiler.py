from __future__ import annotations

from ..plan.events import EventPlan
from .compile_steps import apply_step
from .context import ExecutionContext


def compile_event_plan(plan: EventPlan, ctx: ExecutionContext):
    table = ctx.table(plan.source.table_name)
    for step in plan.steps:
        table = apply_step(step, table=table, source=plan.source, ctx=ctx)
    return table
