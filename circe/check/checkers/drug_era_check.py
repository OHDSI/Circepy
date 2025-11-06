"""
DrugEraCheck class.

This module provides validation for drug era criteria.

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
    from ...cohortdefinition.criteria import CorelatedCriteria, DrugEra
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import CorelatedCriteria, DrugEra


class DrugEraCheck(BaseCorelatedCriteriaCheck):
    """Check for missing days supply information in drug era criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.DrugEraCheck
    """
    
    MISSING_DAYS_INFO = "Using drug era at %s criteria on medical claims (e.g., biologics) may not be accurate due to missing days supply information"
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            INFO severity level
        """
        return WarningSeverity.INFO
    
    def _check_criteria(self, criteria: 'CorelatedCriteria', group_name: str, reporter: WarningReporter) -> None:
        """Check drug era criteria for missing days supply information.
        
        Args:
            criteria: The corelated criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        # Handle case where criteria is still a dict (not yet deserialized)
        if isinstance(criteria, dict):
            # Skip validation for dict-based criteria - they need to be deserialized first
            return
        
        # Ensure criteria has a criteria attribute
        if not hasattr(criteria, 'criteria') or not criteria.criteria:
            return
        
        match_result = Operations.match(criteria.criteria)
        match_result.is_a(DrugEra)
        match_result.then(lambda c: Operations.match(criteria)
                .when(lambda de: (
                    (not criteria.start_window or not criteria.start_window.start) and
                    (not criteria.start_window or not criteria.start_window.end) and
                    (not criteria.end_window or not criteria.end_window.start)
                ))
                .then(lambda de: reporter(self.MISSING_DAYS_INFO, group_name))
            )

