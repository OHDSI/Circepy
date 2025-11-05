"""
InitialEventCheck class.

This module provides validation for initial event criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

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


class InitialEventCheck(BaseCheck):
    """Check for missing initial event criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.InitialEventCheck
    """
    
    NO_INITIAL_EVENT_ERROR = "No initial event criteria specified"
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check for missing initial event criteria.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        match_result = Operations.match(expression)
        match_result.when(lambda e: e.primary_criteria is None or 
                         e.primary_criteria.criteria_list is None or
                         len(e.primary_criteria.criteria_list) == 0)
        match_result.then(lambda e: reporter(self.NO_INITIAL_EVENT_ERROR))

