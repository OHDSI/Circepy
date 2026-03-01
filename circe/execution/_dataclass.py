from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def frozen_slots_dataclass(_cls: type[T] | None = None, **kwargs: Any) -> Any:
    """Compatibility wrapper for frozen+slots dataclasses.

    `slots=True` is preferred for memory/layout guarantees, but this wrapper keeps
    compatibility with older Python runtimes that do not support dataclass slots.
    """

    def wrap(cls: type[T]) -> type[T]:
        try:
            return dataclass(frozen=True, slots=True, **kwargs)(cls)
        except TypeError:
            return dataclass(frozen=True, **kwargs)(cls)

    if _cls is None:
        return wrap
    return wrap(_cls)
