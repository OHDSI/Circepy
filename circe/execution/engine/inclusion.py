from __future__ import annotations

from ..normalize.groups import NormalizedInclusionRule
from .groups import apply_additional_criteria


def apply_inclusion_rules(
    events,
    inclusion_rules: tuple[NormalizedInclusionRule, ...],
    ctx,
):
    if not inclusion_rules:
        return events

    included = events
    for rule in inclusion_rules:
        included = apply_additional_criteria(included, rule.expression, ctx)
    return included
