"""Models for orchestrating groups of cohort definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from ..io import ExpressionInput

SetId = Union[str, int]
CohortId = Union[str, int]


@dataclass(frozen=True)
class CohortDefinitionMember:
    """One cohort member in a definition set."""

    cohort_id: CohortId
    expression: ExpressionInput
    name: Optional[str] = None


@dataclass(frozen=True)
class CohortDefinitionSet:
    """Named collection of cohort definitions for batch generation."""

    set_id: SetId
    set_name: str
    cohorts: List[CohortDefinitionMember]
    version: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = field(default=None)

