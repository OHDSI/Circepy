"""
DeathTimeWindowCheck class.

This module provides validation for death criteria time windows.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning_severity import WarningSeverity
from ..utils.criteria_name_helper import CriteriaNameHelper
from .base_corelated_criteria_check import BaseCorelatedCriteriaCheck
from .warning_reporter import WarningReporter
from .comparisons import Comparisons
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import CorelatedCriteria, Criteria, Death
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import CorelatedCriteria, Criteria, Death


class DeathTimeWindowCheck(BaseCorelatedCriteriaCheck):
    """Check for death criteria with time windows before the index event.
    
    Java equivalent: org.ohdsi.circe.check.checkers.DeathTimeWindowCheck
    """
    
    MESSAGE = "%s attempts to identify death event prior to index event. Events post-death may not be available"
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _internal_check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check death criteria in inclusion rules and other locations.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        super()._internal_check(expression, reporter)
        
        # Check additional criteria
        if expression.additional_criteria:
            self._check_criteria_list(
                expression.additional_criteria.criteria_list,
                self.ADDITIONAL_RULE,
                reporter
            )
        
        # Check primary criteria
        if expression.primary_criteria and expression.primary_criteria.criteria_list:
            self._check_criteria_list(
                expression.primary_criteria.criteria_list,
                self.INITIAL_EVENT,
                reporter
            )
    
    def _check_criteria_list(self, criteria_list, group_name: str, reporter: WarningReporter) -> None:
        """Check a list of criteria.
        
        Args:
            criteria_list: The list of criteria to check
            group_name: The name of the group
            reporter: The warning reporter to use
        """
        if not criteria_list:
            return
        
        for c in criteria_list:
            criteria = None
            if isinstance(c, CorelatedCriteria):
                criteria = c.criteria
                self._check_criteria(c, group_name, reporter)
            elif isinstance(c, Criteria):
                criteria = c
            
            if criteria:
                self._check_criteria_group(criteria, group_name, reporter)
    
    def _check_criteria_group(self, criteria: 'Criteria', group_name: str, reporter: WarningReporter) -> None:
        """Check a criteria and its correlated criteria.
        
        Args:
            criteria: The criteria to check
            group_name: The name of the group
            reporter: The warning reporter to use
        """
        if hasattr(criteria, 'correlated_criteria') and criteria.correlated_criteria:
            correlated = criteria.correlated_criteria
            if hasattr(correlated, 'criteria_list') and correlated.criteria_list:
                for corelated_criteria in correlated.criteria_list:
                    self._check_criteria(corelated_criteria, group_name, reporter)
            if hasattr(correlated, 'groups') and correlated.groups:
                for group in correlated.groups:
                    if hasattr(group, 'criteria_list') and group.criteria_list:
                        for corelated_criteria in group.criteria_list:
                            self._check_criteria(corelated_criteria, group_name, reporter)
    
    def _check_criteria(self, criteria: 'CorelatedCriteria', group_name: str, reporter: WarningReporter) -> None:
        """Check a corelated criteria for death time window issues.
        
        Args:
            criteria: The corelated criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        name = f"{group_name} {CriteriaNameHelper.get_criteria_name(criteria.criteria)}"
        
        match_result = Operations.match(criteria.criteria)
        match_result.is_a(Death)
        match_result.then(lambda death: Operations.match(criteria)
                .when(lambda c: Comparisons.is_before(c.start_window))
                .then(lambda c: reporter(self.MESSAGE, name))
            )

