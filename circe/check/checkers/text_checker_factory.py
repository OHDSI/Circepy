"""
TextCheckerFactory class.

This module provides a factory for checking TextFilter fields in criteria.

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
    from ...cohortdefinition.criteria import (
        Criteria, DemographicCriteria, ConditionOccurrence, DeviceExposure,
        DrugExposure, Observation, Specimen
    )
    from ...cohortdefinition.core import TextFilter
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import (
            Criteria, DemographicCriteria, ConditionOccurrence, DeviceExposure,
            DrugExposure, Observation, Specimen
        )
        from ...cohortdefinition.core import TextFilter


class TextCheckerFactory(BaseCheckerFactory):
    """Factory for checking TextFilter fields in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.TextCheckerFactory
    """
    
    WARNING_EMPTY_VALUE = "%s in the %s has empty %s value"
    
    def __init__(self, reporter: WarningReporter, group_name: str):
        """Initialize a text checker factory.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
        """
        super().__init__(reporter, group_name)
    
    @staticmethod
    def get_factory(reporter: WarningReporter, group_name: str) -> 'TextCheckerFactory':
        """Get a factory instance.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
            
        Returns:
            A new TextCheckerFactory instance
        """
        return TextCheckerFactory(reporter, group_name)
    
    def _get_check_criteria(self, criteria: 'Criteria') -> Callable[['Criteria'], None]:
        """Get a checker function for criteria.
        
        Args:
            criteria: The criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionOccurrence, DeviceExposure, DrugExposure, Observation, Specimen
        )
        
        if isinstance(criteria, ConditionOccurrence):
            def check(c: 'ConditionOccurrence') -> None:
                self._check_text(c.stop_reason, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.STOP_REASON_ATTR)
            return check
        elif isinstance(criteria, DeviceExposure):
            def check(c: 'DeviceExposure') -> None:
                self._check_text(c.unique_device_id, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.UNIQUE_DEVICE_ID_ATTR)
            return check
        elif isinstance(criteria, DrugExposure):
            def check(c: 'DrugExposure') -> None:
                self._check_text(c.stop_reason, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.STOP_REASON_ATTR)
                self._check_text(c.lot_number, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.LOT_NUMBER_ATTR)
            return check
        elif isinstance(criteria, Observation):
            def check(c: 'Observation') -> None:
                self._check_text(c.value_as_string, Constants.Criteria.OBSERVATION, Constants.Attributes.VALUE_AS_STRING_ATTR)
            return check
        elif isinstance(criteria, Specimen):
            def check(c: 'Specimen') -> None:
                self._check_text(c.source_id, Constants.Criteria.SPECIMEN, Constants.Attributes.SOURCE_ID_ATTR)
            return check
        else:
            return lambda c: None  # No text checks for other criteria types
    
    def _get_check_demographic(self, criteria: 'DemographicCriteria') -> Callable[['DemographicCriteria'], None]:
        """Get a checker function for demographic criteria.
        
        Args:
            criteria: The demographic criteria to get a checker for
            
        Returns:
            A function that checks the criteria (no TextFilter in demographic)
        """
        return lambda c: None  # No text filters in demographic criteria
    
    def _check_text(self, text_filter: Optional['TextFilter'], criteria_name: str, attribute: str) -> None:
        """Check if a TextFilter has an empty text value.
        
        Args:
            text_filter: The TextFilter to check
            criteria_name: The name of the criteria type
            attribute: The name of the attribute
        """
        def warning(template: str) -> None:
            self._reporter(template, self._group_name, criteria_name, attribute)
        
        Operations.match(text_filter)\
            .when(lambda tf: tf is not None and tf.text is None)\
            .then(lambda tf: warning(self.WARNING_EMPTY_VALUE))

