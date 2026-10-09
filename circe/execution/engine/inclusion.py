from __future__ import annotations

import ibis

from ..normalize.groups import NormalizedInclusionRule
from .group_keys import event_keys, union_all
from .groups import apply_additional_criteria


def apply_inclusion_rules(
    events,
    inclusion_rules: tuple[NormalizedInclusionRule, ...],
    ctx,
):
    if not inclusion_rules:
        return events

    active_rule_keys = []

    for rule_index, rule in enumerate(inclusion_rules):
        if rule.expression is None or rule.expression.is_empty():
            continue

        matched = apply_additional_criteria(events, rule.expression, ctx)
        active_rule_keys.append(event_keys(matched).mutate(rule_id=ibis.literal(rule_index, type="int64")))

    if not active_rule_keys:
        return events

    if len(active_rule_keys) == 1:
        matched_keys = active_rule_keys[0].select("person_id", "event_id")
    else:
        matched_rules = union_all(active_rule_keys)
        matched_counts = matched_rules.group_by("person_id", "event_id").aggregate(
            matched_rule_count=matched_rules.rule_id.nunique()
        )
        matched_keys = matched_counts.filter(
            matched_counts.matched_rule_count == len(active_rule_keys)
        ).select("person_id", "event_id")

    included = events.join(
        matched_keys,
        predicates=[
            (events.person_id == matched_keys.person_id) & (events.event_id == matched_keys.event_id)
        ],
    )
    return included.select(*[included[c] for c in events.columns])
