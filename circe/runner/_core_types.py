"""Typing helpers shared by runner modules (avoids import cycles)."""

from __future__ import annotations

from typing import Protocol

from ..cohortdefinition import CohortExpression


class CohortDefinitionLike(Protocol):
    cohort_id: int
    cohort_name: str
    expression: CohortExpression


__all__ = ["CohortDefinitionLike"]
