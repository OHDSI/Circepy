"""
NoExitCriteriaCheck class.

This module provides validation for missing exit criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning_severity import WarningSeverity
from .base_check import BaseCheck
from .warning_reporter import WarningReporter
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression


class NoExitCriteriaCheck(BaseCheck):
    """Check for missing exit criteria when all events are selected.
    
    Java equivalent: org.ohdsi.circe.check.checkers.NoExitCriteriaCheck
    """
    
    NO_EXIT_CRITERIA_WARNING = " \"all events\" are selected and cohort exit criteria has not been specified"
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check for missing exit criteria.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        match_result = Operations.match(expression)
        match_result.when(lambda e: (
                e.primary_criteria and
                e.primary_criteria.primary_limit and
                e.primary_criteria.primary_limit.type and
                e.primary_criteria.primary_limit.type.upper() == "ALL" and
                e.end_strategy is None and
                e.expression_limit and
                e.expression_limit.type and
                e.expression_limit.type.upper() == "ALL" and
                (e.additional_criteria is None or
                 (e.qualified_limit and e.qualified_limit.type and e.qualified_limit.type.upper() == "ALL"))
            ))
        match_result.then(lambda e: reporter(self.NO_EXIT_CRITERIA_WARNING))

