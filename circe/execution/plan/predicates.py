from __future__ import annotations

from typing import Any

from .._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class DateRangePredicate:
    op: str | None
    value: Any
    extent: Any


@frozen_slots_dataclass
class NumericRangePredicate:
    op: str | None
    value: float | int | None
    extent: float | int | None
