"""
Validator functions for cohort expressions.

This module provides standalone validator functions that delegate to CohortExpression
methods. These functions provide a functional API for users who prefer it, while the
primary implementation lives in the CohortExpression class methods.

All functions accept a CohortExpression instance and return validation results.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .cohort import CohortExpression


def is_first_event(cohort_expression: "CohortExpression") -> bool:
    """Check if cohort uses first event criteria.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        True if all primary criteria have first=True, False otherwise.

    Example:
        >>> from circe.cohortdefinition import CohortExpression
        >>> cohort = CohortExpression.model_validate(json_data)
        >>> if is_first_event(cohort):
        ...     print("This cohort uses first event criteria")
    """
    return cohort_expression.is_first_event()


def has_exclusion_rules(cohort_expression: "CohortExpression") -> bool:
    """Check if cohort has exclusion rules (inclusion rules).

    Note: In CIRCE terminology, "inclusion rules" act as exclusion criteria.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        True if the cohort has any inclusion rules.

    Example:
        >>> if has_exclusion_rules(cohort):
        ...     print(f"Cohort has {get_exclusion_count(cohort)} exclusion rules")
    """
    return cohort_expression.has_exclusion_rules()


def get_exclusion_count(cohort_expression: "CohortExpression") -> int:
    """Get the number of exclusion rules (inclusion rules).

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        The number of inclusion rules.
    """
    return cohort_expression.get_exclusion_count()


def has_inclusion_rule_by_name(cohort_expression: "CohortExpression", name: str) -> bool:
    """Check if an inclusion rule with the given name exists.

    This is useful for checking if specific rules are shared between cohorts.

    Args:
        cohort_expression: The cohort expression to check.
        name: The name of the inclusion rule to search for.

    Returns:
        True if an inclusion rule with the given name exists.

    Example:
        >>> if has_inclusion_rule_by_name(cohort, "Prior Cancer"):
        ...     print("This cohort excludes patients with prior cancer")
    """
    return cohort_expression.has_inclusion_rule_by_name(name)


def has_censoring_criteria(cohort_expression: "CohortExpression") -> bool:
    """Check if cohort has censoring criteria.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        True if censoring criteria are defined.

    Example:
        >>> if has_censoring_criteria(cohort):
        ...     types = get_censoring_criteria_types(cohort)
        ...     print(f"Censoring on: {', '.join(types)}")
    """
    return cohort_expression.has_censoring_criteria()


def get_censoring_criteria_types(cohort_expression: "CohortExpression") -> list[str]:
    """Get list of censoring criteria class names.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        List of class names (e.g., ['ConditionOccurrence', 'DrugExposure']).
    """
    return cohort_expression.get_censoring_criteria_types()


def has_additional_criteria(cohort_expression: "CohortExpression") -> bool:
    """Check if cohort has additional criteria defined and not empty.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        True if additional criteria are defined and not empty.
    """
    return cohort_expression.has_additional_criteria()


def has_end_strategy(cohort_expression: "CohortExpression") -> bool:
    """Check if cohort has an end strategy defined.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        True if an end strategy is defined.

    Example:
        >>> if has_end_strategy(cohort):
        ...     strategy_type = get_end_strategy_type(cohort)
        ...     print(f"End strategy: {strategy_type}")
    """
    return cohort_expression.has_end_strategy()


def get_end_strategy_type(cohort_expression: "CohortExpression") -> Optional[str]:
    """Get the type of end strategy.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        'DateOffset', 'CustomEra', or None if no end strategy is defined.
    """
    return cohort_expression.get_end_strategy_type()


def get_primary_criteria_types(cohort_expression: "CohortExpression") -> list[str]:
    """Get list of primary criteria class names.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        List of class names (e.g., ['ConditionOccurrence', 'DrugExposure']).

    Example:
        >>> types = get_primary_criteria_types(cohort)
        >>> print(f"Entry events: {', '.join(types)}")
    """
    return cohort_expression.get_primary_criteria_types()


def has_observation_window(cohort_expression: "CohortExpression") -> bool:
    """Check if observation window is defined in primary criteria.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        True if observation window is defined.
    """
    return cohort_expression.has_observation_window()


def get_primary_limit_type(cohort_expression: "CohortExpression") -> Optional[str]:
    """Get the primary limit type.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        The primary limit type (e.g., 'All', 'First') or None.
    """
    return cohort_expression.get_primary_limit_type()


def get_concept_set_count(cohort_expression: "CohortExpression") -> int:
    """Get the number of concept sets.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        The number of concept sets.
    """
    return cohort_expression.get_concept_set_count()


def has_concept_sets(cohort_expression: "CohortExpression") -> bool:
    """Check if concept sets are defined.

    Args:
        cohort_expression: The cohort expression to check.

    Returns:
        True if concept sets are defined.

    Example:
        >>> if has_concept_sets(cohort):
        ...     count = get_concept_set_count(cohort)
        ...     print(f"Cohort uses {count} concept sets")
    """
    return cohort_expression.has_concept_sets()
