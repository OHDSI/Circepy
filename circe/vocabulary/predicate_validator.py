"""
Static validation for concept predicate expressions.

GUARD RAIL: This is a Python-only extension. There is no Java CIRCE-BE equivalent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from circe.vocabulary.concept import ConceptExpressionItem, ConceptSetExpression
from circe.vocabulary.predicate_expressions import (
    ConceptCodeFilter,
    ConceptDateFilter,
    ConceptIdRange,
    ConceptSynonymFilter,
    HierarchyAscend,
    HierarchyDescend,
    ImmediateChildren,
    PredicateExpression,
    SetOperationNode,
    StringFilter,
    VocabularyScope,
)
from circe.vocabulary.predicate_item import ConceptPredicateItem

WarningLevel = Literal["info", "warning", "error"]


@dataclass
class ValidationWarning:
    level: WarningLevel
    message: str
    path: str = ""


class PredicateValidator:
    """Static analysis of concept set definitions before resolution."""

    def validate(self, concept_set: ConceptSetExpression) -> list[ValidationWarning]:
        """Run all validation checks. No database connection needed."""
        warnings: list[ValidationWarning] = []

        if not concept_set.items:
            warnings.append(ValidationWarning("error", "Concept set has no items", "items"))
            return warnings

        all_excluded = True
        for i, item in enumerate(concept_set.items):
            path = f"items[{i}]"
            if isinstance(item, ConceptPredicateItem):
                all_excluded = all_excluded and item.is_excluded
                warnings.extend(self._validate_expression(item.expression, path))
            elif isinstance(item, ConceptExpressionItem):
                all_excluded = all_excluded and item.is_excluded

        if concept_set.items and all_excluded:
            warnings.append(
                ValidationWarning(
                    "warning",
                    "All items are excluded — result will be an empty set",
                    "",
                )
            )

        return warnings

    def _validate_expression(self, expr: PredicateExpression, path: str) -> list[ValidationWarning]:
        warnings: list[ValidationWarning] = []

        if isinstance(expr, VocabularyScope):
            if not expr.domain_id and not expr.concept_class_id:
                warnings.append(
                    ValidationWarning(
                        "warning",
                        "VocabularyScope with no domain_id or concept_class_id constraint — "
                        "may resolve to a large set",
                        f"{path}.expression",
                    )
                )

        elif isinstance(expr, HierarchyDescend):
            if expr.max_depth is not None and expr.max_depth < 1:
                warnings.append(
                    ValidationWarning(
                        "error",
                        "HierarchyDescend.max_depth must be >= 1",
                        f"{path}.expression.max_depth",
                    )
                )

        elif isinstance(expr, StringFilter):
            if not expr.pattern.strip():
                warnings.append(
                    ValidationWarning(
                        "error",
                        "StringFilter pattern is empty",
                        f"{path}.expression.pattern",
                    )
                )
            elif expr.pattern in ("%", "%%"):
                warnings.append(
                    ValidationWarning(
                        "error",
                        "StringFilter pattern is a bare wildcard",
                        f"{path}.expression.pattern",
                    )
                )
            elif len(expr.pattern) <= 3 and not expr.scope:
                warnings.append(
                    ValidationWarning(
                        "warning",
                        f"StringFilter pattern '{expr.pattern}' is very short "
                        f"with no scope — may match many concepts",
                        f"{path}.expression.pattern",
                    )
                )

        elif isinstance(expr, ConceptCodeFilter):
            if not expr.codes:
                warnings.append(
                    ValidationWarning(
                        "error",
                        "ConceptCodeFilter codes list is empty",
                        f"{path}.expression.codes",
                    )
                )
            elif expr.match_type in ("LIKE", "ILIKE"):
                for code in expr.codes:
                    if code in ("%", "%%", ""):
                        warnings.append(
                            ValidationWarning(
                                "error",
                                f"ConceptCodeFilter code '{code}' is empty or bare wildcard",
                                f"{path}.expression.codes",
                            )
                        )

        elif isinstance(expr, ConceptSynonymFilter):
            if not expr.pattern.strip():
                warnings.append(
                    ValidationWarning(
                        "error",
                        "ConceptSynonymFilter pattern is empty",
                        f"{path}.expression.pattern",
                    )
                )
            elif expr.pattern in ("%", "%%"):
                warnings.append(
                    ValidationWarning(
                        "error",
                        "ConceptSynonymFilter pattern is a bare wildcard",
                        f"{path}.expression.pattern",
                    )
                )

        elif isinstance(expr, HierarchyAscend):
            if expr.max_depth is not None and expr.max_depth < 1:
                warnings.append(
                    ValidationWarning(
                        "error",
                        "HierarchyAscend.max_depth must be >= 1",
                        f"{path}.expression.max_depth",
                    )
                )

        elif isinstance(expr, ImmediateChildren):
            pass  # No additional validation needed

        elif isinstance(expr, ConceptIdRange):
            if expr.min_id is None and expr.max_id is None:
                warnings.append(
                    ValidationWarning(
                        "error",
                        "ConceptIdRange requires at least one of min_id or max_id",
                        f"{path}.expression",
                    )
                )

        elif isinstance(expr, ConceptDateFilter):
            if expr.valid_on_date is None and expr.valid_start_date is None and expr.valid_end_date is None:
                warnings.append(
                    ValidationWarning(
                        "error",
                        "ConceptDateFilter requires at least one date constraint",
                        f"{path}.expression",
                    )
                )

        elif isinstance(expr, SetOperationNode):
            if len(expr.operands) < 2:
                warnings.append(
                    ValidationWarning(
                        "error",
                        "SetOperationNode must have at least 2 operands",
                        f"{path}.expression.operands",
                    )
                )
            for j, operand in enumerate(expr.operands):
                warnings.extend(self._validate_expression(operand, f"{path}.expression.operands[{j}]"))

        return warnings
