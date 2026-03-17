from __future__ import annotations

import ibis
import ibis.expr.types as ir

from ...cohortdefinition.criteria import Criteria, InclusionRule
from ..build_context import BuildContext
from .groups import apply_criteria_group
from .registry import build_events


def apply_additional_criteria(events: ir.Table, group, ctx: BuildContext) -> ir.Table:
    return apply_criteria_group(events, group, ctx)


def apply_inclusion_rules(events: ir.Table, rules: list[InclusionRule], ctx: BuildContext) -> ir.Table:
    if not rules:
        return events

    base_events = events.select(events.person_id, events.event_id)
    bit_hits = []
    used_bits: list[int] = []
    for idx, rule in enumerate(rules):
        rule_events = apply_criteria_group(events, rule.expression, ctx)
        if rule_events is None:
            continue
        bit_value = 1 << idx
        used_bits.append(bit_value)
        bit_hits.append(
            rule_events.select(
                rule_events.person_id,
                rule_events.event_id,
                ibis.literal(bit_value, type="int64").name("_rule_bit"),
            ).distinct()
        )
    if not bit_hits:
        return events

    union_hits = bit_hits[0]
    for table in bit_hits[1:]:
        union_hits = union_hits.union(table, distinct=False)

    union_hits = ctx.maybe_materialize(union_hits, label="inclusion_hits", analyze=True)

    mask = union_hits.group_by(union_hits.person_id, union_hits.event_id).aggregate(
        # Postgres returns NUMERIC for SUM(BIGINT), which breaks bitwise ops.
        # Ibis also infers SUM(int64) -> int64 and may optimize away an int64 cast,
        # so we force an intermediate cast to keep the SQL-level cast.
        _rule_mask=union_hits._rule_bit.sum().cast("decimal(38,0)").cast("int64")
    )
    target_mask = sum(used_bits)
    target_literal = ibis.literal(target_mask, type="int64")
    mask = mask.filter((mask._rule_mask & target_literal) == target_literal)

    filtered_ids = base_events.inner_join(mask, ["person_id", "event_id"])
    return events.inner_join(filtered_ids, ["person_id", "event_id"]).select(events.columns)


def apply_censoring(events: ir.Table, criteria_list: list[Criteria], ctx: BuildContext) -> ir.Table:
    if not criteria_list:
        return events
    censor_tables = [build_events(criteria, ctx) for criteria in criteria_list if criteria]
    if not censor_tables:
        return events
    censor_events = censor_tables[0]
    for table in censor_tables[1:]:
        censor_events = censor_events.union(table)

    censor_events = censor_events.select(
        censor_events.person_id,
        censor_events.start_date.name("censor_start"),
    )
    joined = events.join(
        censor_events,
        (events.person_id == censor_events.person_id) & (censor_events.censor_start >= events.start_date),
        how="left",
    )
    min_censor = joined.group_by(joined.person_id, joined.event_id).aggregate(
        censor_date=joined.censor_start.min()
    )
    event_columns = events.columns
    events = events.left_join(
        min_censor,
        (events.person_id == min_censor.person_id) & (events.event_id == min_censor.event_id),
    )
    events = events.select(*event_columns, min_censor.censor_date)
    events = events.mutate(
        end_date=ibis.ifelse(
            events.censor_date.notnull() & (events.censor_date < events.end_date),
            events.censor_date,
            events.end_date,
        )
    ).select(*event_columns)
    return events


def apply_censor_window(events: ir.Table, window, ctx: BuildContext) -> ir.Table:
    if not window:
        return events
    if window.start_date:
        events = events.filter(events.start_date >= ibis.timestamp(window.start_date))
    if window.end_date:
        events = events.filter(events.end_date <= ibis.timestamp(window.end_date))
    return events
