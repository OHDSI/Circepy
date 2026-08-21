from __future__ import annotations

from circe.cohortdefinition.criteria import ObservationPeriod
from circe.extensions import lowerer

from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan
from .common import lower_standard_domain_plan


@lowerer(ObservationPeriod)
def lower_observation_period(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    return lower_standard_domain_plan(criterion, criterion_index=criterion_index)
