"""
Base corelated criteria check class for validation checks.

This module provides the base class for checks that validate corelated criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .base_iterable_check import BaseIterableCheck
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import Criteria, CorelatedCriteria
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import Criteria, CorelatedCriteria


class BaseCorelatedCriteriaCheck(BaseIterableCheck):
    """Base class for checks that validate corelated criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.BaseCorelatedCriteriaCheck
    
    This class provides functionality to iterate over corelated criteria
    in inclusion rules.
    """
    
    def _internal_check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Internal check that iterates over corelated criteria.
        
        Args:
            expression: The cohort expression to validate
            reporter: The warning reporter to use
        """
        if expression.inclusion_rules:
            for inclusion_rule in expression.inclusion_rules:
                if inclusion_rule.expression and inclusion_rule.expression.criteria_list:
                    for criteria in inclusion_rule.expression.criteria_list:
                        # Skip if criteria is still a dict (shouldn't happen after deserialization, but be defensive)
                        if isinstance(criteria, dict):
                            continue
                        group_name = f"{self.INCLUSION_RULE}{inclusion_rule.name}"
                        self._check_criteria(criteria, group_name, reporter)
                        if hasattr(criteria, 'criteria') and criteria.criteria:
                            self._check_criteria_group(criteria.criteria, group_name, reporter)
    
    def _check_criteria_group(self, criteria: 'Criteria', group_name: str, reporter: WarningReporter) -> None:
        """Check correlated criteria groups.
        
        Args:
            criteria: The criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        # Skip if criteria is still a dict (not yet deserialized)
        if isinstance(criteria, dict):
            return
        
        if hasattr(criteria, 'correlated_criteria') and criteria.correlated_criteria:
            correlated = criteria.correlated_criteria
            if hasattr(correlated, 'criteria_list') and correlated.criteria_list:
                for corelated_criteria in correlated.criteria_list:
                    # Skip dicts
                    if isinstance(corelated_criteria, dict):
                        continue
                    self._check_criteria(corelated_criteria, group_name, reporter)
                    if hasattr(corelated_criteria, 'criteria') and corelated_criteria.criteria:
                        self._check_criteria_group(corelated_criteria.criteria, group_name, reporter)
            if hasattr(correlated, 'groups') and correlated.groups:
                for group in correlated.groups:
                    if hasattr(group, 'criteria_list') and group.criteria_list:
                        for corelated_criteria in group.criteria_list:
                            # Skip dicts
                            if isinstance(corelated_criteria, dict):
                                continue
                            self._check_criteria(corelated_criteria, group_name, reporter)
                            if hasattr(corelated_criteria, 'criteria') and corelated_criteria.criteria:
                                self._check_criteria_group(corelated_criteria.criteria, group_name, reporter)
    
    def _check_criteria(self, criteria: 'CorelatedCriteria', group_name: str, reporter: WarningReporter) -> None:
        """Check a single corelated criteria (to be implemented by subclasses).
        
        Args:
            criteria: The corelated criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        # Skip if criteria is still a dict (not yet deserialized)
        # This can happen when Pydantic doesn't fully deserialize polymorphic types
        if isinstance(criteria, dict):
            return
        
        raise NotImplementedError("Subclasses must implement _check_criteria")

