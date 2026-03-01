from __future__ import annotations

from typing import Tuple

from .._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class GroupPredicate:
    mode: str
    count: int | None = None
    children: Tuple["GroupPredicate", ...] = ()
