from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

if TYPE_CHECKING:
    from ibis.expr.types import Table as IbisTable

    Table: TypeAlias = IbisTable
else:  # pragma: no cover - typing-only fallback when ibis is not installed
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
