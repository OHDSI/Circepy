"""
AttributeCheckerFactory class.

This module provides a factory for checking attributes in criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Callable, Any
from ..constants import Constants
from .base_checker_factory import BaseCheckerFactory
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.criteria import Criteria, DemographicCriteria
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import Criteria, DemographicCriteria


class AttributeCheckerFactory(BaseCheckerFactory):
    """Factory for checking attributes in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.AttributeCheckerFactory
    """
    
    WARNING_EMPTY_VALUE = "%s in the %s does not have attributes"
    
    def __init__(self, reporter: WarningReporter, group_name: str):
        """Initialize an attribute checker factory.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
        """
        super().__init__(reporter, group_name)
    
    @staticmethod
    def get_factory(reporter: WarningReporter, group_name: str) -> 'AttributeCheckerFactory':
        """Get a factory instance.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
            
        Returns:
            A new AttributeCheckerFactory instance
        """
        return AttributeCheckerFactory(reporter, group_name)
    
    def _get_check_criteria(self, criteria: 'Criteria') -> Callable[['Criteria'], None]:
        """Get a checker function for criteria.
        
        Args:
            criteria: The criteria to get a checker for
            
        Returns:
            A function that checks the criteria (non-demographic criteria don't need attribute checks)
        """
        return lambda c: None  # Non-demographic criteria don't need attribute checks
    
    def _get_check_demographic(self, criteria: 'DemographicCriteria') -> Callable[['DemographicCriteria'], None]:
        """Get a checker function for demographic criteria.
        
        Args:
            criteria: The demographic criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        def check(c: 'DemographicCriteria') -> None:
            self._check_attribute(
                Constants.Criteria.DEMOGRAPHIC,
                c.age,
                c.gender,
                c.race,
                c.ethnicity,
                c.occurrence_start_date if hasattr(c, 'occurrence_start_date') else None,
                c.occurrence_end_date if hasattr(c, 'occurrence_end_date') else None
            )
        return check
    
    def _check_attribute(self, criteria_name: str, *attributes: Any) -> None:
        """Check if any attributes are present.
        
        Args:
            criteria_name: The name of the criteria type
            *attributes: The attribute values to check
        """
        has_value = any(attr is not None for attr in attributes)
        if not has_value:
            self._reporter(self.WARNING_EMPTY_VALUE, self._group_name, criteria_name)

