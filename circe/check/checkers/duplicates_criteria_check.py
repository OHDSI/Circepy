"""
DuplicatesCriteriaCheck class.

This module provides validation for duplicate criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Tuple
from ..warning_severity import WarningSeverity
from ..utils.criteria_name_helper import CriteriaNameHelper
from .base_criteria_check import BaseCriteriaCheck
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import Criteria
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import Criteria


class DuplicatesCriteriaCheck(BaseCriteriaCheck):
    """Check for duplicate criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.DuplicatesCriteriaCheck
    """
    
    DUPLICATE_WARNING = "Probably %s duplicates %s"
    
    def __init__(self):
        """Initialize the duplicates criteria check."""
        super().__init__()
        self._criteria_list: List[Tuple[str, 'Criteria']] = []
    
    def _after_check(self, reporter: WarningReporter, expression: 'CohortExpression') -> None:
        """Check for duplicates after all criteria have been collected.
        
        Args:
            reporter: The warning reporter to use
            expression: The cohort expression that was checked
        """
        if len(self._criteria_list) > 1:
            for i in range(len(self._criteria_list) - 1):
                criteria, criteria_obj = self._criteria_list[i]
                duplicates = [
                    (name, obj) for name, obj in self._criteria_list[i + 1:]
                    if self._compare_criteria(criteria_obj, obj)
                ]
                if duplicates:
                    names = ", ".join(name for name, _ in duplicates)
                    reporter(self.DUPLICATE_WARNING, criteria, names)
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _compare_criteria(self, c1: 'Criteria', c2: 'Criteria') -> bool:
        """Compare two criteria to see if they are duplicates.
        
        Args:
            c1: The first criteria
            c2: The second criteria
            
        Returns:
            True if the criteria are duplicates, False otherwise
        """
        if type(c1) != type(c2):
            return False
        
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ObservationPeriod, ProcedureOccurrence, Specimen,
            VisitOccurrence, VisitDetail, PayerPlanPeriod
        )
        
        if isinstance(c1, ConditionEra):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, ConditionOccurrence):
            return (c1.codeset_id == c2.codeset_id and 
                   c1.condition_source_concept == c2.condition_source_concept)
        elif isinstance(c1, Death):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, DeviceExposure):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, DoseEra):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, DrugEra):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, DrugExposure):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, Measurement):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, Observation):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, ObservationPeriod):
            # For ObservationPeriod, compare all fields
            return (self._compare_objects(c1.period_start_date, c2.period_start_date) and
                   self._compare_objects(c1.period_end_date, c2.period_end_date) and
                   self._compare_objects(c1.period_length, c2.period_length))
        elif isinstance(c1, ProcedureOccurrence):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, Specimen):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, VisitOccurrence):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, VisitDetail):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, PayerPlanPeriod):
            return (c1.payer_concept == c2.payer_concept and
                   c1.payer_source_concept == c2.payer_source_concept and
                   c1.plan_concept == c2.plan_concept and
                   c1.plan_source_concept == c2.plan_source_concept and
                   c1.sponsor_concept == c2.sponsor_concept and
                   c1.sponsor_source_concept == c2.sponsor_source_concept and
                   c1.stop_reason_concept == c2.stop_reason_concept and
                   c1.stop_reason_source_concept == c2.stop_reason_source_concept)
        
        # Fallback to reflection-based comparison
        return self._compare_objects_reflection(c1, c2)
    
    def _compare_objects(self, obj1, obj2) -> bool:
        """Compare two objects for equality.
        
        Args:
            obj1: First object
            obj2: Second object
            
        Returns:
            True if objects are equal, False otherwise
        """
        return obj1 == obj2
    
    def _compare_objects_reflection(self, obj1, obj2) -> bool:
        """Compare objects using equality (Pydantic models support this).
        
        Args:
            obj1: First object
            obj2: Second object
            
        Returns:
            True if objects are equal, False otherwise
        """
        return obj1 == obj2
    
    def _check_criteria(self, criteria: 'Criteria', group_name: str, reporter: WarningReporter) -> None:
        """Collect criteria for duplicate checking.
        
        Args:
            criteria: The criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use (not used here, but kept for interface)
        """
        criteria_name = CriteriaNameHelper.get_criteria_name(criteria) + " criteria in " + group_name
        self._criteria_list.append((criteria_name, criteria))

