from __future__ import annotations

from ..ibis.context import ExecutionContext
from ..lower.criteria import lower_criterion
from ..normalize.cohort import NormalizedCohort
from ..plan.cohort import CohortPlan, PrimaryEventInput
from .censoring import apply_censoring
from .collapse import collapse_events
from .end_strategy import apply_end_strategy
from .groups import apply_additional_criteria
from .inclusion import apply_inclusion_rules
from .primary import build_primary_events


def build_cohort_table(normalized: NormalizedCohort, ctx: ExecutionContext):
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
    )
    primary_events = build_primary_events(cohort_plan, ctx)
    qualified_events = apply_additional_criteria(
        primary_events, normalized.additional_criteria, ctx
    )
    included_events = apply_inclusion_rules(qualified_events, normalized.inclusion_rules, ctx)
    ended_events = apply_end_strategy(included_events, normalized.end_strategy, ctx)
    censored_events = apply_censoring(
        ended_events,
        normalized.censoring_criteria,
        normalized.censor_window,
        ctx,
    )
    return collapse_events(
        censored_events,
        normalized.collapse_settings,
        normalized.censor_window,
    )
