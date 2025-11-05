"""
OcurrenceCheck class.

This module provides validation for occurrence criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning_severity import WarningSeverity
from .base_corelated_criteria_check import BaseCorelatedCriteriaCheck
from .warning_reporter import WarningReporter
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.criteria import CorelatedCriteria, Occurrence
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import CorelatedCriteria, Occurrence


class OcurrenceCheck(BaseCorelatedCriteriaCheck):
    """Check for invalid occurrence values (at least 0).
    
    Java equivalent: org.ohdsi.circe.check.checkers.OcurrenceCheck
    """
    
    AT_LEAST_0_WARNING = "'at least 0' occurrence is not a real constraint, probably meant 'exactly 0' or 'at least 1'"
    AT_LEAST = 2
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _check_criteria(self, criteria: 'CorelatedCriteria', group_name: str, reporter: WarningReporter) -> None:
        """Check occurrence for invalid values.
        
        Args:
            criteria: The corelated criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        if criteria.occurrence:
            match_result = Operations.match(criteria.occurrence)
            match_result.when(lambda o: o.type == self.AT_LEAST and o.count == 0)
            match_result.then(lambda o: reporter(self.AT_LEAST_0_WARNING))

