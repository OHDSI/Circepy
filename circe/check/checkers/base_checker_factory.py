"""
Base checker factory class.

This module provides the base class for checker factories that create
checker functions for different criteria types.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Callable
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.criteria import Criteria, DemographicCriteria
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import Criteria, DemographicCriteria


class BaseCheckerFactory:
    """Base class for checker factories.
    
    Java equivalent: org.ohdsi.circe.check.checkers.BaseCheckerFactory
    
    This class provides the infrastructure for factories that create
    checker functions for validating criteria.
    """
    
    def __init__(self, reporter: WarningReporter, group_name: str):
        """Initialize a checker factory.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
        """
        self._group_name = group_name
        self._reporter = reporter
    
    @property
    def group_name(self) -> str:
        """Get the group name."""
        return self._group_name
    
    @property
    def reporter(self) -> WarningReporter:
        """Get the warning reporter."""
        return self._reporter
    
    def _get_check_criteria(self, criteria: 'Criteria') -> Callable[['Criteria'], None]:
        """Get a checker function for a criteria (to be implemented by subclasses).
        
        Args:
            criteria: The criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        raise NotImplementedError("Subclasses must implement _get_check_criteria")
    
    def _get_check_demographic(self, criteria: 'DemographicCriteria') -> Callable[['DemographicCriteria'], None]:
        """Get a checker function for a demographic criteria (to be implemented by subclasses).
        
        Args:
            criteria: The demographic criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        raise NotImplementedError("Subclasses must implement _get_check_demographic")
    
    def check(self, criteria) -> None:
        """Check a criteria (supports both Criteria and DemographicCriteria).
        
        Args:
            criteria: The criteria to check (Criteria or DemographicCriteria)
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import Criteria, DemographicCriteria
        
        if isinstance(criteria, DemographicCriteria):
            checker = self._get_check_demographic(criteria)
            checker(criteria)
        elif isinstance(criteria, Criteria):
            checker = self._get_check_criteria(criteria)
            checker(criteria)

