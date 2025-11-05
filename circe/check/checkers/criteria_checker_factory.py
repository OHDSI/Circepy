"""
CriteriaCheckerFactory class.

This module provides a factory for checking if criteria use a specific concept set.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Callable, List, Optional
from .base_checker_factory import BaseCheckerFactory
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...vocabulary.concept import ConceptSet
    from ...cohortdefinition.criteria import (
        Criteria, ConditionEra, ConditionOccurrence, Death, DeviceExposure,
        DoseEra, DrugEra, DrugExposure, Measurement, Observation,
        ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail,
        LocationRegion
    )
    from ...cohortdefinition.core import ConceptSetSelection
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...vocabulary.concept import ConceptSet
        from ...cohortdefinition.criteria import (
            Criteria, ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail,
            LocationRegion
        )
        from ...cohortdefinition.core import ConceptSetSelection


class CriteriaCheckerFactory:
    """Factory for checking if criteria use a specific concept set.
    
    Java equivalent: org.ohdsi.circe.check.checkers.CriteriaCheckerFactory
    
    Note: This is not a BaseCheckerFactory subclass - it has a different purpose.
    It's used to check if a criteria uses a specific concept set.
    """
    
    def __init__(self, concept_set: 'ConceptSet'):
        """Initialize a criteria checker factory.
        
        Args:
            concept_set: The concept set to check for
        """
        self._concept_set = concept_set
    
    @staticmethod
    def get_factory(concept_set: 'ConceptSet') -> 'CriteriaCheckerFactory':
        """Get a factory instance.
        
        Args:
            concept_set: The concept set to check for
            
        Returns:
            A new CriteriaCheckerFactory instance
        """
        return CriteriaCheckerFactory(concept_set)
    
    def get_criteria_checker(self, criteria: 'Criteria') -> Callable[['Criteria'], bool]:
        """Get a checker function that returns True if the criteria uses the concept set.
        
        Args:
            criteria: The criteria to get a checker for
            
        Returns:
            A function that returns True if the criteria uses the concept set
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail,
            LocationRegion
        )
        from ...cohortdefinition.core import ConceptSetSelection
        
        def check_condition_era(c: 'ConditionEra') -> bool:
            return c.codeset_id == self._concept_set.id
        
        def check_condition_occurrence(c: 'ConditionOccurrence') -> bool:
            return (c.codeset_id == self._concept_set.id or 
                   c.condition_source_concept == self._concept_set.id)
        
        def check_death(c: 'Death') -> bool:
            return c.codeset_id == self._concept_set.id
        
        def check_device_exposure(c: 'DeviceExposure') -> bool:
            return (c.codeset_id == self._concept_set.id or 
                   c.device_source_concept == self._concept_set.id)
        
        def check_dose_era(c: 'DoseEra') -> bool:
            return c.codeset_id == self._concept_set.id
        
        def check_drug_era(c: 'DrugEra') -> bool:
            return c.codeset_id == self._concept_set.id
        
        def check_drug_exposure(c: 'DrugExposure') -> bool:
            return (c.codeset_id == self._concept_set.id or 
                   c.drug_source_concept == self._concept_set.id)
        
        def check_measurement(c: 'Measurement') -> bool:
            return (c.codeset_id == self._concept_set.id or 
                   c.measurement_source_concept == self._concept_set.id)
        
        def check_observation(c: 'Observation') -> bool:
            return (c.codeset_id == self._concept_set.id or 
                   c.observation_source_concept == self._concept_set.id)
        
        def check_procedure_occurrence(c: 'ProcedureOccurrence') -> bool:
            return (c.codeset_id == self._concept_set.id or 
                   c.procedure_source_concept == self._concept_set.id)
        
        def check_specimen(c: 'Specimen') -> bool:
            return c.codeset_id == self._concept_set.id
        
        def check_visit_occurrence(c: 'VisitOccurrence') -> bool:
            return c.codeset_id == self._concept_set.id
        
        def check_visit_detail(c: 'VisitDetail') -> bool:
            if c.codeset_id == self._concept_set.id:
                return True
            # Check ConceptSetSelection fields
            suppliers = self._get_concept_set_selection_suppliers(c)
            for supplier in suppliers:
                css = supplier()
                if css is not None and css.codeset_id == self._concept_set.id:
                    return True
            return False
        
        def check_location_region(c: 'LocationRegion') -> bool:
            return c.codeset_id == self._concept_set.id
        
        def default_check(c: 'Criteria') -> bool:
            return False
        
        # Route to appropriate checker
        if isinstance(criteria, ConditionEra):
            return check_condition_era
        elif isinstance(criteria, ConditionOccurrence):
            return check_condition_occurrence
        elif isinstance(criteria, Death):
            return check_death
        elif isinstance(criteria, DeviceExposure):
            return check_device_exposure
        elif isinstance(criteria, DoseEra):
            return check_dose_era
        elif isinstance(criteria, DrugEra):
            return check_drug_era
        elif isinstance(criteria, DrugExposure):
            return check_drug_exposure
        elif isinstance(criteria, Measurement):
            return check_measurement
        elif isinstance(criteria, Observation):
            return check_observation
        elif isinstance(criteria, ProcedureOccurrence):
            return check_procedure_occurrence
        elif isinstance(criteria, Specimen):
            return check_specimen
        elif isinstance(criteria, VisitOccurrence):
            return check_visit_occurrence
        elif isinstance(criteria, VisitDetail):
            return check_visit_detail
        elif isinstance(criteria, LocationRegion):
            return check_location_region
        else:
            return default_check
    
    def _get_concept_set_selection_suppliers(self, criteria: 'VisitDetail') -> List[Callable[[], Optional['ConceptSetSelection']]]:
        """Get suppliers for ConceptSetSelection fields in VisitDetail.
        
        Args:
            criteria: The VisitDetail criteria
            
        Returns:
            A list of functions that return ConceptSetSelection objects
        """
        suppliers: List[Callable[[], Optional['ConceptSetSelection']]] = []
        suppliers.append(lambda: criteria.place_of_service_cs)
        suppliers.append(lambda: criteria.gender_cs)
        suppliers.append(lambda: criteria.provider_specialty_cs)
        suppliers.append(lambda: criteria.visit_detail_type_cs)
        return suppliers

