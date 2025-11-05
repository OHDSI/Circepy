"""
CriteriaContradictionsCheck class.

This module provides validation for contradictory criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Tuple, Optional
from ..warning_severity import WarningSeverity
from ..utils.criteria_name_helper import CriteriaNameHelper
from .base_corelated_criteria_check import BaseCorelatedCriteriaCheck
from .warning_reporter import WarningReporter
from .comparisons import Comparisons

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import CorelatedCriteria, Occurrence
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import CorelatedCriteria, Occurrence


class CriteriaInfo:
    """Information about a criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.CriteriaContradictionsCheck.CriteriaInto
    """
    
    def __init__(self, name: str, criteria: 'CorelatedCriteria'):
        """Initialize criteria info.
        
        Args:
            name: The name of the criteria
            criteria: The corelated criteria
        """
        self._name = name
        self._criteria = criteria
    
    @property
    def name(self) -> str:
        """Get the name."""
        return self._name
    
    @property
    def criteria(self) -> 'CorelatedCriteria':
        """Get the criteria."""
        return self._criteria


class CriteriaContradictionsCheck(BaseCorelatedCriteriaCheck):
    """Check for contradictory occurrence criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.CriteriaContradictionsCheck
    """
    
    WARNING = "%s might be contradicted with %s and possibly will lead to 0 records"
    
    def __init__(self):
        """Initialize the criteria contradictions check."""
        super().__init__()
        self._criteria_list: List[CriteriaInfo] = []
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _check_criteria(self, criteria: 'CorelatedCriteria', group_name: str, reporter: WarningReporter) -> None:
        """Collect criteria information.
        
        Args:
            criteria: The corelated criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        name = f"{group_name} {CriteriaNameHelper.get_criteria_name(criteria.criteria)}"
        self._criteria_list.append(CriteriaInfo(name, criteria))
    
    def _after_check(self, reporter: WarningReporter, expression: 'CohortExpression') -> None:
        """Check for contradictions after all criteria have been collected.
        
        Args:
            reporter: The warning reporter to use
            expression: The cohort expression that was checked
        """
        if len(self._criteria_list) > 1:
            size = len(self._criteria_list)
            for i in range(size - 1):
                info = self._criteria_list[i]
                for other_info in self._criteria_list[i + 1:]:
                    if (Comparisons.compare_criteria(info.criteria.criteria, other_info.criteria.criteria) and
                        self._check_contradiction(info.criteria.occurrence, other_info.criteria.occurrence)):
                        reporter(self.WARNING, info.name, other_info.name)
    
    def _check_contradiction(self, o1: Optional['Occurrence'], o2: Optional['Occurrence']) -> bool:
        """Check if two occurrences contradict each other.
        
        Args:
            o1: The first occurrence
            o2: The second occurrence
            
        Returns:
            True if the occurrences contradict, False otherwise
        """
        if o1 is None or o2 is None:
            return False
        
        range1 = self._get_occurrence_range(o1)
        range2 = self._get_occurrence_range(o2)
        
        # Check if ranges overlap
        return not self._ranges_overlap(range1, range2)
    
    def _get_occurrence_range(self, occurrence: 'Occurrence') -> Tuple[int, int]:
        """Get the range of valid occurrence counts.
        
        Args:
            occurrence: The occurrence to get range for
            
        Returns:
            A tuple of (min, max) values
        """
        # EXACTLY = 0, AT_MOST = 1, AT_LEAST = 2
        if occurrence.type == 0:  # EXACTLY
            return (occurrence.count, occurrence.count)
        elif occurrence.type == 1:  # AT_MOST
            return (float('-inf'), occurrence.count)
        elif occurrence.type == 2:  # AT_LEAST
            return (occurrence.count, float('inf'))
        else:
            return (float('-inf'), float('inf'))
    
    def _ranges_overlap(self, range1: Tuple[int, int], range2: Tuple[int, int]) -> bool:
        """Check if two ranges overlap.
        
        Args:
            range1: First range (min, max)
            range2: Second range (min, max)
            
        Returns:
            True if ranges overlap, False otherwise
        """
        min1, max1 = range1
        min2, max2 = range2
        
        # Handle infinity
        if min1 == float('-inf'):
            min1 = float('-inf')
        if max1 == float('inf'):
            max1 = float('inf')
        if min2 == float('-inf'):
            min2 = float('-inf')
        if max2 == float('inf'):
            max2 = float('inf')
        
        # Check if ranges overlap
        return not (max1 < min2 or max2 < min1)

