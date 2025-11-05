"""
ExitCriteriaDaysOffsetCheck class.

This module provides validation for exit criteria days offset.

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
    from ...cohortdefinition.core import DateOffsetStrategy, DateType
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.core import DateOffsetStrategy, DateType


class ExitCriteriaDaysOffsetCheck(BaseCheck):
    """Check for invalid days offset in exit criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.ExitCriteriaDaysOffsetCheck
    """
    
    DAYS_OFFSET_WARNING = "Cohort Exit criteria: Days offset from start date should be greater than 0"
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check exit criteria days offset.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        match_result = Operations.match(expression.end_strategy)
        match_result.is_a(DateOffsetStrategy)
        match_result.then(lambda s: Operations.match(s)
                .when(lambda dos: dos.date_field == DateType.START_DATE and dos.offset == 0)
                .then(lambda dos: reporter(self.DAYS_OFFSET_WARNING))
            )

