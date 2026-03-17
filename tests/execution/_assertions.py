from __future__ import annotations

from circe.execution.plan.schema import STANDARD_EVENT_COLUMNS


def assert_standard_event_columns(columns) -> None:
    """Assert a table-like object exposes the canonical standard event schema."""
    normalized = tuple(columns)
    assert normalized == STANDARD_EVENT_COLUMNS
