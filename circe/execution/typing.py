from __future__ import annotations

from typing import Any, Protocol

from typing_extensions import TypeAlias

# Ibis does not currently ship usable type information for its table expressions.
# Treat them as `Any` at the compatibility boundary rather than propagating
# `import-untyped` errors through the executor.
Table: TypeAlias = Any


class IbisBackendLike(Protocol):
    """Minimal backend surface required by the Ibis executor."""

    def table(self, name: str, database: str | None = None) -> Table: ...

    def create_table(
        self,
        name: str,
        /,
        obj: Any = None,
        *,
        schema: Any | None = None,
        database: str | None = None,
        temp: bool = False,
        overwrite: bool = False,
    ) -> Any: ...
