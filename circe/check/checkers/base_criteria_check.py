"""
Base criteria check class for validation checks.

This module provides the base class for checks that validate criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Optional
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


class BaseCriteriaCheck(BaseIterableCheck):
    """Base class for checks that validate criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.BaseCriteriaCheck
    
    This class provides functionality to iterate over criteria in
    primary criteria and inclusion rules.
    """
    
    def _internal_check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Internal check that iterates over criteria.
        
        Args:
            expression: The cohort expression to validate
            reporter: The warning reporter to use
        """
        if expression.primary_criteria and expression.primary_criteria.criteria_list:
            for criteria in expression.primary_criteria.criteria_list:
                self._check_criteria_group(criteria, self.INITIAL_EVENT, reporter)
        
        if expression.inclusion_rules:
            for inclusion_rule in expression.inclusion_rules:
                if inclusion_rule.expression and inclusion_rule.expression.criteria_list:
                    for criteria in inclusion_rule.expression.criteria_list:
                        group_name = f"{self.INCLUSION_RULE}{inclusion_rule.name}"
                        self._check_criteria_group(
                            criteria.criteria if hasattr(criteria, 'criteria') else criteria,
                            group_name,
                            reporter
                        )
    
    def _check_criteria_group(self, criteria: 'Criteria', group_name: str, reporter: WarningReporter) -> None:
        """Check a criteria and its correlated criteria.
        
        Args:
            criteria: The criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        self._check_criteria(criteria, group_name, reporter)
        
        # Check correlated criteria if present
        if hasattr(criteria, 'correlated_criteria') and criteria.correlated_criteria:
            correlated = criteria.correlated_criteria
            if hasattr(correlated, 'criteria_list') and correlated.criteria_list:
                for corelated_criteria in correlated.criteria_list:
                    self._check_criteria_group(corelated_criteria.criteria, group_name, reporter)
            if hasattr(correlated, 'groups') and correlated.groups:
                for group in correlated.groups:
                    if hasattr(group, 'criteria_list') and group.criteria_list:
                        for corelated_criteria in group.criteria_list:
                            self._check_criteria_group(corelated_criteria.criteria, group_name, reporter)
    
    def _check_criteria(self, criteria: 'Criteria', group_name: str, reporter: WarningReporter) -> None:
        """Check a single criteria (to be implemented by subclasses).
        
        Args:
            criteria: The criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        raise NotImplementedError("Subclasses must implement _check_criteria")

