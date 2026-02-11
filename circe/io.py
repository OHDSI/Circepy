"""
Input loading helpers for cohort expressions.

This module provides a canonical loader used by execution-oriented APIs to
accept either in-memory models or serialized payloads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Union

from .api import cohort_expression_from_json
from .cohortdefinition import CohortExpression

ExpressionInput = Union[CohortExpression, Mapping[str, Any], str, Path]


def load_expression(value: ExpressionInput) -> CohortExpression:
    """Normalize different expression inputs into a CohortExpression.

    Accepted inputs:
    - CohortExpression
    - mapping/dict compatible with CohortExpression
    - JSON string
    - path to a JSON file
    """
    if isinstance(value, CohortExpression):
        return value

    if isinstance(value, Mapping):
        return CohortExpression.model_validate(dict(value))

    if isinstance(value, Path):
        return cohort_expression_from_json(value.read_text(encoding="utf-8"))

    if isinstance(value, str):
        stripped = value.strip()

        # JSON payload path
        if stripped.startswith("{") or stripped.startswith("["):
            return cohort_expression_from_json(stripped)

        # File-system path
        path = Path(value)
        if path.exists() and path.is_file():
            return cohort_expression_from_json(path.read_text(encoding="utf-8"))

        # If it wasn't an existing path, attempt JSON parse for clearer errors.
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Expected JSON string or path to a JSON file for cohort expression input."
            ) from exc
        return CohortExpression.model_validate(parsed)

    raise TypeError(
        "Unsupported expression input type. Expected CohortExpression, mapping, JSON string, or Path."
    )
