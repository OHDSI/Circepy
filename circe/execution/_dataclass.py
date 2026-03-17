from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Callable, TypeVar, cast, overload

from typing_extensions import dataclass_transform

T = TypeVar("T")


@overload
def frozen_slots_dataclass(_cls: type[T], **kwargs: Any) -> type[T]: ...


@overload
def frozen_slots_dataclass(_cls: None = None, **kwargs: Any) -> Callable[[type[T]], type[T]]: ...


@dataclass_transform(frozen_default=True)
def frozen_slots_dataclass(
    _cls: type[T] | None = None,
    **kwargs: Any,
) -> type[T] | Callable[[type[T]], type[T]]:
    """Compatibility wrapper for frozen+slots dataclasses.

    `slots=True` is preferred for memory/layout guarantees, but this wrapper keeps
    compatibility with older Python runtimes that do not support dataclass slots.
    """

    def wrap(cls: type[T]) -> type[T]:
        dataclass_factory = cast(Any, dataclass)
        if sys.version_info >= (3, 10):
            return cast(type[T], dataclass_factory(frozen=True, slots=True, **kwargs)(cls))
        return cast(type[T], dataclass_factory(frozen=True, **kwargs)(cls))

    if _cls is None:
        return wrap
    return wrap(_cls)
