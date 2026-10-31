"""Refinement operators for decomposable cohort definitions.

A refinement is a narrowing or tail-modifying edit that the v1 Circe format
already places at a fixed pipeline checkpoint.  ``parent + refinement`` therefore
flattens to a stand-alone v1 expression (see
:meth:`circe.decomposition.Decomposition.flatten`), which is what makes shared
execution safe: everything before the earliest touched checkpoint is reused and
everything after is recomputed by the same stage functions.

Operators are intentionally expressed with the original v1 model classes so a
flattened definition is a normal :class:`~circe.cohortdefinition.CohortExpression`
that can be written to JSON, rendered to SQL, or executed one cohort at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from ..cohortdefinition import CohortExpression
from ..vocabulary.concept import ConceptSet

__all__ = [
    "AddCensoring",
    "AddConceptSets",
    "AddInclusionRule",
    "Refinement",
    "RequireAtEntry",
    "SetCensorWindow",
    "SetCollapse",
    "SetEndStrategy",
    "SetExpressionLimit",
    "SetQualifiedLimit",
    "SetTitle",
]


class Refinement:
    """Base class for a reversible, v1-placeable edit to a cohort expression."""

    kind: ClassVar[str] = "refinement"

    def apply(self, expression: CohortExpression) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def describe(self) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        return {"operator": self.kind, "description": self.describe()}


@dataclass(frozen=True)
class RequireAtEntry(Refinement):
    """AND a group into the entry (additional) criteria."""

    group: Any
    kind: ClassVar[str] = "require_at_entry"

    def apply(self, expression: CohortExpression) -> None:
        expression.additional_criteria = self.group.model_copy(deep=True)

    def describe(self) -> str:
        return "RequireAtEntry"


@dataclass(frozen=True)
class AddInclusionRule(Refinement):
    """Append one inclusion rule (ANDed over qualified events)."""

    rule: Any
    kind: ClassVar[str] = "add_inclusion_rule"

    def apply(self, expression: CohortExpression) -> None:
        expression.inclusion_rules = [*expression.inclusion_rules, self.rule.model_copy(deep=True)]

    def describe(self) -> str:
        name = getattr(self.rule, "name", None)
        return f"AddInclusionRule({name!r})" if name else "AddInclusionRule"


@dataclass(frozen=True)
class SetQualifiedLimit(Refinement):
    """Set the qualified-events limit (``first``/``last``)."""

    limit: Any
    kind: ClassVar[str] = "set_qualified_limit"

    def apply(self, expression: CohortExpression) -> None:
        expression.qualified_limit = self.limit.model_copy(deep=True) if self.limit is not None else None

    def describe(self) -> str:
        return f"SetQualifiedLimit({_limit_label(self.limit)})"


@dataclass(frozen=True)
class SetExpressionLimit(Refinement):
    """Set the final expression limit (``first``/``last``)."""

    limit: Any
    kind: ClassVar[str] = "set_expression_limit"

    def apply(self, expression: CohortExpression) -> None:
        expression.expression_limit = self.limit.model_copy(deep=True) if self.limit is not None else None

    def describe(self) -> str:
        return f"SetExpressionLimit({_limit_label(self.limit)})"


@dataclass(frozen=True)
class SetEndStrategy(Refinement):
    """Replace the end strategy (runs after the expression limit)."""

    strategy: Any
    kind: ClassVar[str] = "set_end_strategy"

    def apply(self, expression: CohortExpression) -> None:
        expression.end_strategy = self.strategy.model_copy(deep=True) if self.strategy is not None else None

    def describe(self) -> str:
        return f"SetEndStrategy({type(self.strategy).__name__ if self.strategy else 'none'})"


@dataclass(frozen=True)
class AddCensoring(Refinement):
    """Append one censoring criterion."""

    criterion: Any
    kind: ClassVar[str] = "add_censoring"

    def apply(self, expression: CohortExpression) -> None:
        expression.censoring_criteria = [
            *expression.censoring_criteria,
            self.criterion.model_copy(deep=True),
        ]

    def describe(self) -> str:
        return f"AddCensoring({type(self.criterion).__name__})"


@dataclass(frozen=True)
class SetCensorWindow(Refinement):
    """Replace the censor window."""

    window: Any
    kind: ClassVar[str] = "set_censor_window"

    def apply(self, expression: CohortExpression) -> None:
        expression.censor_window = self.window.model_copy(deep=True) if self.window is not None else None

    def describe(self) -> str:
        return f"SetCensorWindow({getattr(self.window, 'start_date', None)}..{getattr(self.window, 'end_date', None)})"


@dataclass(frozen=True)
class SetCollapse(Refinement):
    """Replace the era-collapse settings."""

    settings: Any
    kind: ClassVar[str] = "set_collapse"

    def apply(self, expression: CohortExpression) -> None:
        expression.collapse_settings = (
            self.settings.model_copy(deep=True) if self.settings is not None else None
        )

    def describe(self) -> str:
        pad = getattr(self.settings, "era_pad", None)
        return f"SetCollapse(era_pad={pad})"


@dataclass(frozen=True)
class AddConceptSets(Refinement):
    """Add concept sets introduced by a derived cohort's refinements."""

    concept_sets: tuple[ConceptSet, ...]
    kind: ClassVar[str] = "add_concept_sets"

    def apply(self, expression: CohortExpression) -> None:
        existing = {int(concept_set.id) for concept_set in expression.concept_sets}
        expression.concept_sets = [
            *expression.concept_sets,
            *[
                concept_set.model_copy(deep=True)
                for concept_set in self.concept_sets
                if int(concept_set.id) not in existing
            ],
        ]

    def describe(self) -> str:
        return f"AddConceptSets({len(self.concept_sets)})"


@dataclass(frozen=True)
class SetTitle(Refinement):
    """Copy the derived cohort's display title (metadata only)."""

    title: str | None
    kind: ClassVar[str] = "set_title"

    def apply(self, expression: CohortExpression) -> None:
        expression.title = self.title

    def describe(self) -> str:
        return f"SetTitle({self.title!r})"


def _limit_label(limit: Any) -> str:
    value = getattr(limit, "type", None)
    return str(value).lower() if value else "all"
