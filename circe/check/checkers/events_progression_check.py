"""
EventsProgressionCheck class.

This module provides validation for event progression limits.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from enum import Enum
from typing import Optional
from ..warning_severity import WarningSeverity
from .base_check import BaseCheck
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.core import ResultLimit
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.core import ResultLimit


class LimitType(Enum):
    """Limit type enum with weights.
    
    Java equivalent: org.ohdsi.circe.check.checkers.EventsProgressionCheck.LimitType
    """
    NONE = (0, None)
    EARLIEST = (0, "First")
    LATEST = (1, "Last")
    ALL = (2, "All")
    
    def __init__(self, weight: int, name: Optional[str]):
        """Initialize a limit type.
        
        Args:
            weight: The weight for progression comparison
            name: The name string for matching
        """
        self._weight = weight
        self._name = name
    
    @property
    def weight(self) -> int:
        """Get the weight of this limit type.
        
        Returns:
            The weight value
        """
        return self._weight
    
    @property
    def name(self) -> Optional[str]:
        """Get the name of this limit type.
        
        Returns:
            The name string
        """
        return self._name
    
    @staticmethod
    def from_name(name: Optional[str]) -> 'LimitType':
        """Get a limit type from its name.
        
        Args:
            name: The name to match
            
        Returns:
            The matching LimitType, or NONE if not found
        """
        if name is None:
            return LimitType.NONE
        for limit_type in LimitType:
            if limit_type.name and limit_type.name == name:
                return limit_type
        return LimitType.NONE


class EventsProgressionCheck(BaseCheck):
    """Check for event progression limit issues.
    
    Java equivalent: org.ohdsi.circe.check.checkers.EventsProgressionCheck
    """
    
    WARNING = "%s limit may not have intended effect since it breaks all/latest/earliest progression"
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check for event progression issues.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        if not expression.primary_criteria:
            return
        
        initial_weight = self._get_weight(expression.primary_criteria.primary_limit)
        cohort_initial_weight = self._get_weight(expression.qualified_limit)
        
        # Qualifying limit is ignored when no additionalCriteria specified
        if expression.additional_criteria is not None:
            qualifying_weight = self._get_weight(expression.expression_limit)
        else:
            qualifying_weight = LimitType.NONE.weight
        
        if initial_weight - cohort_initial_weight < 0:
            reporter(self.WARNING, "Cohort of initial events")
        
        if (cohort_initial_weight - qualifying_weight < 0 or 
            initial_weight - qualifying_weight < 0):
            reporter(self.WARNING, "Qualifying cohort")
    
    def _get_weight(self, limit: Optional['ResultLimit']) -> int:
        """Get the weight for a result limit.
        
        Args:
            limit: The result limit to get weight for
            
        Returns:
            The weight value
        """
        if limit is None or limit.type is None:
            return LimitType.NONE.weight
        return LimitType.from_name(limit.type).weight

