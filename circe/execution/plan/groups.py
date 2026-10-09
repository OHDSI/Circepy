from __future__ import annotations

from .._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class GroupPredicate:
    mode: str
    count: int | None = None
    children: tuple[GroupPredicate, ...] = ()
