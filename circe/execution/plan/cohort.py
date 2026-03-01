from __future__ import annotations

from typing import Tuple

from .._dataclass import frozen_slots_dataclass
from ..normalize.groups import NormalizedCriteriaGroup
from ..normalize.windows import NormalizedObservationWindow
from .events import EventPlan


@frozen_slots_dataclass
class PrimaryEventInput:
    event_plan: EventPlan
    correlated_criteria: NormalizedCriteriaGroup | None = None


@frozen_slots_dataclass
class CohortPlan:
    primary_event_plans: Tuple[PrimaryEventInput, ...]
    observation_window: NormalizedObservationWindow | None
    primary_limit_type: str
