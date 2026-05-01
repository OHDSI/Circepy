"""
Input loading helpers for cohort expressions.

This module provides a canonical loader used by execution-oriented APIs to
accept either in-memory models or serialized payloads.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Union

from .api import cohort_expression_from_json, cohort_expression_from_yaml
from .cohortdefinition import CohortExpression
from .cohortdefinition.yaml_utils import cohort_expression_to_snake_case

ExpressionInput = Union[CohortExpression, Mapping[str, Any], str, Path]


def load_expression(value: ExpressionInput) -> CohortExpression:
    """Normalize different expression inputs into a CohortExpression.

    Accepted inputs:
    - CohortExpression
    - mapping/dict compatible with CohortExpression
    - JSON string
    - YAML string
    - path to a JSON or YAML file
    """
    if isinstance(value, CohortExpression):
        return value

    if isinstance(value, Mapping):
        return CohortExpression.model_validate(dict(value))

    if isinstance(value, Path):
        content = value.read_text(encoding="utf-8")
        if value.suffix in (".yaml", ".yml"):
            return cohort_expression_from_yaml(content)
        else:
            return cohort_expression_from_json(content)

    if isinstance(value, str):
        stripped = value.strip()

        # JSON payload path
        if stripped.startswith("{") or stripped.startswith("["):
            return cohort_expression_from_json(stripped)

        # File-system path
        path = Path(value)
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8")
            if path.suffix in (".yaml", ".yml"):
                return cohort_expression_from_yaml(content)
            else:
                return cohort_expression_from_json(content)

        # If it wasn't an existing path, attempt JSON parse for clearer errors.
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Expected JSON string, YAML string, or path to a JSON/YAML file for cohort expression input."
            ) from exc
        return CohortExpression.model_validate(parsed)

    raise TypeError(
        "Unsupported expression input type. Expected CohortExpression, mapping, JSON/YAML string, or Path."
    )


def save_expression_as_yaml(expr: CohortExpression, path: str | Path) -> None:
    """Save a CohortExpression as a YAML file with snake_case field names.

    Args:
        expr: CohortExpression instance to save
        path: File path to save the YAML file to
    """
    import yaml

    path = Path(path)
    yaml_dict = cohort_expression_to_snake_case(expr)

    # Write to file with nice YAML formatting
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            yaml_dict,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
