"""
TimePatternCheck class.

This module provides validation for time window patterns.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional
from collections import Counter
from ..warning_severity import WarningSeverity
from ..utils.criteria_name_helper import CriteriaNameHelper
from .base_corelated_criteria_check import BaseCorelatedCriteriaCheck
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import CorelatedCriteria
    from ...cohortdefinition.core import Window
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import CorelatedCriteria
        from ...cohortdefinition.core import Window


class TimeWindowInfo:
    """Information about a time window.
    
    Java equivalent: org.ohdsi.circe.check.checkers.TimePatternCheck.TimeWindowInfo
    """
    
    def __init__(self, name: str, start: Optional['Window'], end: Optional['Window']):
        """Initialize time window info.
        
        Args:
            name: The name of the criteria
            start: The start window
            end: The end window
        """
        self._name = name
        self._start = start
        self._end = end
    
    @property
    def name(self) -> str:
        """Get the name."""
        return self._name
    
    @property
    def start(self) -> Optional['Window']:
        """Get the start window."""
        return self._start
    
    @property
    def end(self) -> Optional['Window']:
        """Get the end window."""
        return self._end


class TimePatternCheck(BaseCorelatedCriteriaCheck):
    """Check for inconsistent time window patterns.
    
    Java equivalent: org.ohdsi.circe.check.checkers.TimePatternCheck
    """
    
    def __init__(self):
        """Initialize the time pattern check."""
        super().__init__()
        self._time_window_info_list: List[TimeWindowInfo] = []
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            INFO severity level
        """
        return WarningSeverity.INFO
    
    def _check_criteria(self, criteria: 'CorelatedCriteria', group_name: str, reporter: WarningReporter) -> None:
        """Collect time window information.
        
        Args:
            criteria: The corelated criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        name = f"{CriteriaNameHelper.get_criteria_name(criteria.criteria)} criteria at {group_name}"
        self._time_window_info_list.append(
            TimeWindowInfo(name, criteria.start_window, criteria.end_window)
        )
    
    def _after_check(self, reporter: WarningReporter, expression: 'CohortExpression') -> None:
        """Check for inconsistent time window patterns.
        
        Args:
            reporter: The warning reporter to use
            expression: The cohort expression that was checked
        """
        if len(self._time_window_info_list) <= 1:
            return
        
        # Calculate start days for each time window
        start_days = [self._start_days(info.start) for info in self._time_window_info_list]
        
        # Count frequency of each start day value
        freq = Counter(start_days)
        max_freq = max(freq.values()) if freq else 0
        
        if max_freq > 1:
            # Find the most common pattern
            most_common_value = max(freq, key=freq.get)
            most_common_info = next(
                (info for info in self._time_window_info_list 
                 if self._start_days(info.start) == most_common_value),
                None
            )
            
            if most_common_info:
                most_common_pattern = self._format_time_window(most_common_info)
                for info in self._time_window_info_list:
                    start = self._start_days(info.start)
                    curr_freq = freq.get(start, 0)
                    if max_freq - curr_freq > 0:
                        reporter(
                            "%s time window differs from most common pattern prior '%s', shouldn't that be a valid pattern?",
                            info.name,
                            most_common_pattern
                        )
    
    def _format_time_window(self, ti: TimeWindowInfo) -> str:
        """Format a time window as a string.
        
        Args:
            ti: The time window info to format
            
        Returns:
            A formatted string describing the time window
        """
        result = ""
        if ti.start and ti.start.start:
            result += f"{self._format_days(ti.start.start)} days {self._format_coeff(ti.start.start)}"
        if ti.start and ti.start.end:
            result += f" and {self._format_days(ti.start.end)} days {self._format_coeff(ti.start.end)}"
        return result
    
    def _format_days(self, endpoint: Optional['Window.Endpoint']) -> str:
        """Format days from an endpoint.
        
        Args:
            endpoint: The endpoint to format
            
        Returns:
            A string representation of the days
        """
        if endpoint is None or endpoint.days is None:
            return "all"
        return str(endpoint.days)
    
    def _format_coeff(self, endpoint: Optional['Window.Endpoint']) -> str:
        """Format coefficient from an endpoint.
        
        Args:
            endpoint: The endpoint to format
            
        Returns:
            "before " if negative, "after " if positive
        """
        if endpoint is None:
            return ""
        return "before " if endpoint.coeff < 0 else "after "
    
    def _start_days(self, window: Optional['Window']) -> int:
        """Calculate start days from a window.
        
        Args:
            window: The window to calculate from
            
        Returns:
            The calculated start days value
        """
        if window is None or window.start is None:
            return 0
        days = window.start.days if window.start.days is not None else 0
        return days * window.start.coeff

