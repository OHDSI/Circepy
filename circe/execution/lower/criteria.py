from __future__ import annotations

from typing import Protocol

from circe.extensions import get_registry

from ..errors import UnsupportedCriterionError
from ..normalize.criteria import NormalizedCriterion
from ..plan.events import EventPlan


class LowerFn(Protocol):
    def __call__(
        self,
        criterion: NormalizedCriterion,
        *,
        criterion_index: int,
    ) -> EventPlan: ...


def lower_criterion(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    registry = get_registry()
    criteria_cls = type(criterion.raw_criteria)
    lowerer = registry.get_lowerer(criteria_cls)

    if lowerer is not None:
        return lowerer(criterion, criterion_index=criterion_index)

    raise UnsupportedCriterionError(
        f"Ibis executor lowering error: no lowerer registered for {criterion.criterion_type}."
    )
