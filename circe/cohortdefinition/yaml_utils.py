"""Utilities for YAML conversion with snake_case naming."""

import re
from typing import Any

from circe.cohortdefinition.cohort import CohortExpression


def to_snake_case(name: str) -> str:
    """Convert camelCase or PascalCase string to snake_case.

    Args:
        name: String in camelCase or PascalCase format

    Returns:
        String in snake_case format
    """
    # Insert underscore before uppercase letters preceded by lowercase
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    # Insert underscore before uppercase letters preceded by lowercase or numbers
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def to_pascal_case(name: str) -> str:
    """Convert snake_case string to PascalCase.

    Args:
        name: String in snake_case format

    Returns:
        String in PascalCase format
    """
    components = name.split("_")
    return "".join(x.title() for x in components)


def dict_to_snake_case(data: Any) -> Any:
    """Recursively convert all dict keys from PascalCase/camelCase to snake_case.

    Args:
        data: Dictionary, list, or primitive value

    Returns:
        Same structure with all dict keys converted to snake_case
    """
    if isinstance(data, dict):
        return {to_snake_case(key): dict_to_snake_case(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [dict_to_snake_case(item) for item in data]
    else:
        return data


def dict_to_pascal_case(data: Any) -> Any:
    """Recursively convert all dict keys from snake_case to PascalCase.

    Args:
        data: Dictionary, list, or primitive value

    Returns:
        Same structure with all dict keys converted to PascalCase
    """
    if isinstance(data, dict):
        return {to_pascal_case(key): dict_to_pascal_case(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [dict_to_pascal_case(item) for item in data]
    else:
        return data


def cohort_expression_to_snake_case(expr: CohortExpression) -> dict[str, Any]:
    """Convert CohortExpression to dict with snake_case field names.

    Args:
        expr: CohortExpression instance

    Returns:
        Dictionary representation with all keys in snake_case
    """
    # Use model_dump to convert to dict with serialization aliases
    expr_dict = expr.model_dump(by_alias=True)
    # Convert all keys to snake_case
    return dict_to_snake_case(expr_dict)


def snake_case_dict_to_cohort_expression(data: dict[str, Any]) -> CohortExpression:
    """Convert snake_case dict to CohortExpression.

    Args:
        data: Dictionary with snake_case keys

    Returns:
        CohortExpression instance
    """
    # CohortExpression models have populate_by_name=True which accepts snake_case
    # So we can pass the data directly without conversion
    try:
        return CohortExpression.model_validate(data)
    except Exception:
        # If that fails, try converting to PascalCase as fallback
        pascal_dict = dict_to_pascal_case(data)
        return CohortExpression.model_validate(pascal_dict)
