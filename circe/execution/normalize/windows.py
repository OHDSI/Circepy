from __future__ import annotations

from typing import Any, Optional

from ...cohortdefinition.core import (
    DateRange,
    NumericRange,
    ObservationFilter,
    Period,
    Window,
    WindowBound,
)
from .._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class NormalizedDateRange:
    op: str | None
    value: Any
    extent: Any


@frozen_slots_dataclass
class NormalizedNumericRange:
    op: str | None
    value: float | int | None
    extent: float | int | None


@frozen_slots_dataclass
class NormalizedObservationWindow:
    prior_days: int
    post_days: int


@frozen_slots_dataclass
class NormalizedPeriod:
    start_date: str | None
    end_date: str | None


@frozen_slots_dataclass
class NormalizedWindowBound:
    coeff: int
    days: int | None


@frozen_slots_dataclass
class NormalizedWindow:
    start: NormalizedWindowBound | None
    end: NormalizedWindowBound | None
    use_event_end: bool | None
    use_index_end: bool | None


def normalize_date_range(value: Optional[DateRange]) -> Optional[NormalizedDateRange]:
    if value is None:
        return None
    return NormalizedDateRange(op=value.op, value=value.value, extent=value.extent)


def normalize_numeric_range(
    value: Optional[NumericRange],
) -> Optional[NormalizedNumericRange]:
    if value is None:
        return None
    return NormalizedNumericRange(op=value.op, value=value.value, extent=value.extent)


def normalize_observation_window(
    value: Optional[ObservationFilter],
) -> Optional[NormalizedObservationWindow]:
    if value is None:
        return None
    return NormalizedObservationWindow(
        prior_days=int(value.prior_days),
        post_days=int(value.post_days),
    )


def normalize_period(value: Optional[Period]) -> Optional[NormalizedPeriod]:
    if value is None:
        return None
    return NormalizedPeriod(start_date=value.start_date, end_date=value.end_date)


def normalize_window_bound(
    value: Optional[WindowBound],
) -> Optional[NormalizedWindowBound]:
    if value is None:
        return None
    return NormalizedWindowBound(coeff=int(value.coeff), days=value.days)


def normalize_window(value: Optional[Window]) -> Optional[NormalizedWindow]:
    if value is None:
        return None
    return NormalizedWindow(
        start=normalize_window_bound(value.start),
        end=normalize_window_bound(value.end),
        use_event_end=value.use_event_end,
        use_index_end=value.use_index_end,
    )
