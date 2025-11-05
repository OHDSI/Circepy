"""
TimeWindowCheck class.

This module provides validation for time window ranges.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Optional
from ..warning_severity import WarningSeverity
from ..utils.criteria_name_helper import CriteriaNameHelper
from .base_corelated_criteria_check import BaseCorelatedCriteriaCheck
from .warning_reporter import WarningReporter
from .comparisons import Comparisons
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import CorelatedCriteria
    from ...cohortdefinition.core import ObservationFilter
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import CorelatedCriteria
        from ...cohortdefinition.core import ObservationFilter


class TimeWindowCheck(BaseCorelatedCriteriaCheck):
    """Check for time window ranges that are longer than required.
    
    Java equivalent: org.ohdsi.circe.check.checkers.TimeWindowCheck
    """
    
    WARNING = "%s criteria have time window range that is longer than required time for initial event"
    
    def __init__(self):
        """Initialize the time window check."""
        super().__init__()
        self._observation_filter: Optional['ObservationFilter'] = None
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            INFO severity level
        """
        return WarningSeverity.INFO
    
    def _before_check(self, reporter: WarningReporter, expression: 'CohortExpression') -> None:
        """Store the observation filter before checking.
        
        Args:
            reporter: The warning reporter
            expression: The cohort expression being validated
        """
        if expression.primary_criteria:
            self._observation_filter = expression.primary_criteria.observation_window
    
    def _check_criteria(self, criteria: 'CorelatedCriteria', group_name: str, reporter: WarningReporter) -> None:
        """Check criteria for time window issues.
        
        Args:
            criteria: The corelated criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        name = f"{group_name} {CriteriaNameHelper.get_criteria_name(criteria.criteria)}"
        
        match_result = Operations.match(criteria)
        match_result.when(lambda c: c.start_window is not None and
                         self._observation_filter is not None and
                         Comparisons.compare_to(self._observation_filter, c.start_window) < 0)
        match_result.then(lambda c: reporter(self.WARNING, name))

