"""
Attrition functions for CohortComposer.

These functions define inclusion and exclusion rules that filter the cohort
after the initial entry event. Modeled after OHDSI/Capr's attrition function.
"""

from dataclasses import dataclass, field
from typing import Optional, Union

from circe.capr.criteria import Criteria, CriteriaGroup


@dataclass
class AttritionRule:
    """
    Represents a named attrition rule (inclusion/exclusion criterion).

    Attributes:
        name: Human-readable name for the rule (used in attrition reports)
        description: Optional detailed description
        expression: CriteriaGroup defining the rule logic
    """

    name: str
    description: Optional[str] = None
    expression: Optional[CriteriaGroup] = None


@dataclass
class AttritionRules:
    """
    Collection of attrition rules to apply to the cohort.

    Attributes:
        rules: List of AttritionRule objects in order of application
    """

    rules: list[AttritionRule] = field(default_factory=list)


def attrition(**named_rules: Union[CriteriaGroup, Criteria]) -> AttritionRules:
    """
    Define attrition rules for the cohort.

    Args:
        **named_rules: Keyword arguments where name is the rule name
                      and value is a CriteriaGroup or Criteria

    Returns:
        AttritionRules object containing all defined rules

    Example:
        >>> attrition(
        ...     no_prior_insulin=with_all(
        ...         exactly(0, drug_exposure(insulin_cs), aperture)
        ...     ),
        ...     has_t2dm_diagnosis=with_all(
        ...         at_least(1, condition_occurrence(t2dm_cs), aperture)
        ...     )
        ... )

    Note:
        Rule names should be descriptive as they appear in attrition reports.
        Use underscores for multi-word names; they will be displayed with spaces.
    """
    rules = []
    for name, expression in named_rules.items():
        # Convert single Criteria to CriteriaGroup if needed
        if isinstance(expression, Criteria):
            expression = CriteriaGroup(group_type="ALL", criteria_list=[expression])

        # Convert underscores to spaces for display
        display_name = name.replace("_", " ")

        rules.append(AttritionRule(name=display_name, expression=expression))

    return AttritionRules(rules=rules)


def inclusion_rule(
    name: str, expression: Union[CriteriaGroup, Criteria], description: Optional[str] = None
) -> AttritionRule:
    """
    Create a single named inclusion rule.

    Args:
        name: Human-readable name for the rule
        expression: CriteriaGroup or Criteria defining the rule
        description: Optional detailed description

    Returns:
        AttritionRule object

    Example:
        >>> rule = inclusion_rule(
        ...     name="Has HbA1c within 6 months",
        ...     expression=at_least(1, measurement(hba1c_cs), aperture),
        ...     description="Patient must have HbA1c measurement within 6 months after index"
        ... )
    """
    if isinstance(expression, Criteria):
        expression = CriteriaGroup(group_type="ALL", criteria_list=[expression])

    return AttritionRule(name=name, expression=expression, description=description)
