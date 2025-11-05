"""
ConceptSetSelectionCheckerFactory class.

This module provides a factory for checking ConceptSetSelection in criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Callable, Optional
from ..constants import Constants
from .base_checker_factory import BaseCheckerFactory
from .warning_reporter import WarningReporter
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.criteria import Criteria, DemographicCriteria, VisitDetail
    from ...cohortdefinition.core import ConceptSetSelection
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import Criteria, DemographicCriteria, VisitDetail
        from ...cohortdefinition.core import ConceptSetSelection


class ConceptSetSelectionCheckerFactory(BaseCheckerFactory):
    """Factory for checking ConceptSetSelection in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.ConceptSetSelectionCheckerFactory
    """
    
    WARNING_EMPTY_VALUE = "%s in the %s has empty %s value"
    
    def __init__(self, reporter: WarningReporter, group_name: str):
        """Initialize a concept set selection checker factory.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
        """
        super().__init__(reporter, group_name)
    
    @staticmethod
    def get_factory(reporter: WarningReporter, group_name: str) -> 'ConceptSetSelectionCheckerFactory':
        """Get a factory instance.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
            
        Returns:
            A new ConceptSetSelectionCheckerFactory instance
        """
        return ConceptSetSelectionCheckerFactory(reporter, group_name)
    
    def _get_check_criteria(self, criteria: 'Criteria') -> Callable[['Criteria'], None]:
        """Get a checker function for criteria.
        
        Args:
            criteria: The criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import VisitDetail
        
        if isinstance(criteria, VisitDetail):
            def check(c: 'VisitDetail') -> None:
                self._check_concept_set_selection(
                    c.visit_detail_type_cs, Constants.Criteria.VISIT_DETAIL, Constants.Attributes.VISIT_DETAIL_TYPE_ATTR
                )
                self._check_concept_set_selection(
                    c.gender_cs, Constants.Criteria.VISIT_DETAIL, Constants.Attributes.GENDER_ATTR
                )
                self._check_concept_set_selection(
                    c.provider_specialty_cs, Constants.Criteria.VISIT_DETAIL, Constants.Attributes.PROVIDER_SPECIALITY_ATTR
                )
                self._check_concept_set_selection(
                    c.place_of_service_cs, Constants.Criteria.VISIT_DETAIL, Constants.Attributes.PLACE_OF_SERVICE_ATTR
                )
            return check
        else:
            return lambda c: None  # No ConceptSetSelection checks for other criteria types
    
    def _get_check_demographic(self, criteria: 'DemographicCriteria') -> Callable[['DemographicCriteria'], None]:
        """Get a checker function for demographic criteria.
        
        Args:
            criteria: The demographic criteria to get a checker for
            
        Returns:
            A function that checks the criteria (no ConceptSetSelection in demographic)
        """
        return lambda c: None  # No ConceptSetSelection in demographic criteria
    
    def _check_concept_set_selection(
        self, 
        concept_set_selection: Optional['ConceptSetSelection'], 
        criteria_name: str, 
        attribute: str
    ) -> None:
        """Check if a ConceptSetSelection has an empty codesetId.
        
        Args:
            concept_set_selection: The ConceptSetSelection to check
            criteria_name: The name of the criteria type
            attribute: The name of the attribute
        """
        def warning(template: str) -> None:
            self._reporter(template, self._group_name, criteria_name, attribute)
        
        Operations.match(concept_set_selection)\
            .when(lambda css: css is not None and css.codeset_id is None)\
            .then(lambda css: warning(self.WARNING_EMPTY_VALUE))

