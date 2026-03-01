from __future__ import annotations

from typing import Any, TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ibis.expr.types import Table
else:  # pragma: no cover - typing-only fallback when ibis is not installed
    Table = Any


class IbisBackendLike(Protocol):
    """Minimal backend surface required by the Ibis executor."""

    def table(self, name: str, database: str | None = None) -> Table: ...


# Backward-compatible alias for existing imports.
BackendLike = IbisBackendLike
