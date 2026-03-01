from __future__ import annotations

from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import lower_standard_domain_plan


def lower_visit_occurrence(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    return lower_standard_domain_plan(criterion, criterion_index=criterion_index)
