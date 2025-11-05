"""
ConceptCheckerFactory class.

This module provides a factory for checking concept arrays in criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Callable, List, Optional
from ..constants import Constants
from .base_checker_factory import BaseCheckerFactory
from .warning_reporter import WarningReporter
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.criteria import (
        Criteria, DemographicCriteria, ConditionEra, ConditionOccurrence,
        Death, DeviceExposure, DoseEra, DrugEra, DrugExposure, Measurement,
        Observation, ObservationPeriod, ProcedureOccurrence, Specimen,
        VisitOccurrence, PayerPlanPeriod
    )
    from ...vocabulary.concept import Concept
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import (
            Criteria, DemographicCriteria, ConditionEra, ConditionOccurrence,
            Death, DeviceExposure, DoseEra, DrugEra, DrugExposure, Measurement,
            Observation, ObservationPeriod, ProcedureOccurrence, Specimen,
            VisitOccurrence, PayerPlanPeriod
        )
        from ...vocabulary.concept import Concept


class ConceptCheckerFactory(BaseCheckerFactory):
    """Factory for checking concept arrays in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.ConceptCheckerFactory
    """
    
    WARNING_EMPTY_VALUE = "%s in the %s has empty %s value"
    
    def __init__(self, reporter: WarningReporter, group_name: str):
        """Initialize a concept checker factory.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
        """
        super().__init__(reporter, group_name)
    
    @staticmethod
    def get_factory(reporter: WarningReporter, group_name: str) -> 'ConceptCheckerFactory':
        """Get a factory instance.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
            
        Returns:
            A new ConceptCheckerFactory instance
        """
        return ConceptCheckerFactory(reporter, group_name)
    
    def _get_check_criteria(self, criteria: 'Criteria') -> Callable[['Criteria'], None]:
        """Get a checker function for criteria.
        
        Args:
            criteria: The criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ObservationPeriod, ProcedureOccurrence, Specimen,
            VisitOccurrence, PayerPlanPeriod
        )
        
        def check_condition_era(c: 'ConditionEra') -> None:
            self._check_concept(c.gender, Constants.Criteria.CONDITION_ERA, Constants.Attributes.GENDER_ATTR)
        
        def check_condition_occurrence(c: 'ConditionOccurrence') -> None:
            self._check_concept(c.condition_type, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.CONDITION_TYPE_ATTR)
            self._check_concept(c.gender, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.GENDER_ATTR)
            self._check_concept(c.provider_specialty, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR)
            self._check_concept(c.visit_type, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.VISIT_TYPE_ATTR)
        
        def check_death(c: 'Death') -> None:
            self._check_concept(c.death_type, Constants.Criteria.DEATH, Constants.Attributes.DEATH_TYPE_ATTR)
            self._check_concept(c.gender, Constants.Criteria.DEATH, Constants.Attributes.GENDER_ATTR)
        
        def check_device_exposure(c: 'DeviceExposure') -> None:
            self._check_concept(c.device_type, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.DEVICE_TYPE_ATTR)
            self._check_concept(c.gender, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.GENDER_ATTR)
            self._check_concept(c.provider_specialty, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR)
            self._check_concept(c.visit_type, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.VISIT_TYPE_ATTR)
        
        def check_dose_era(c: 'DoseEra') -> None:
            self._check_concept(c.unit, Constants.Criteria.DOSE_ERA, Constants.Attributes.UNIT_ATTR)
            self._check_concept(c.gender, Constants.Criteria.DOSE_ERA, Constants.Attributes.GENDER_ATTR)
        
        def check_drug_era(c: 'DrugEra') -> None:
            self._check_concept(c.gender, Constants.Criteria.DRUG_ERA, Constants.Attributes.GENDER_ATTR)
        
        def check_drug_exposure(c: 'DrugExposure') -> None:
            self._check_concept(c.drug_type, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.DRUG_TYPE_ATTR)
            self._check_concept(c.route_concept, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.ROUTE_CONCEPT_ATTR)
            self._check_concept(c.dose_unit, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.DOSE_UNIT_ATTR)
            self._check_concept(c.gender, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.GENDER_ATTR)
            self._check_concept(c.provider_specialty, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR)
            self._check_concept(c.visit_type, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.VISIT_TYPE_ATTR)
        
        def check_measurement(c: 'Measurement') -> None:
            self._check_concept(c.measurement_type, Constants.Criteria.MEASUREMENT, Constants.Attributes.MEASUREMENT_TYPE_ATTR)
            self._check_concept(c.operator, Constants.Criteria.MEASUREMENT, Constants.Attributes.OPERATOR_ATTR)
            self._check_concept(c.value_as_concept, Constants.Criteria.MEASUREMENT, Constants.Attributes.VALUE_AS_CONCEPT_ATTR)
            self._check_concept(c.unit, Constants.Criteria.MEASUREMENT, Constants.Attributes.UNIT_ATTR)
            self._check_concept(c.gender, Constants.Criteria.MEASUREMENT, Constants.Attributes.GENDER_ATTR)
            self._check_concept(c.provider_specialty, Constants.Criteria.MEASUREMENT, Constants.Attributes.PROVIDER_SPECIALITY_ATTR)
            self._check_concept(c.visit_type, Constants.Criteria.MEASUREMENT, Constants.Attributes.VISIT_TYPE_ATTR)
        
        def check_observation(c: 'Observation') -> None:
            self._check_concept(c.observation_type, Constants.Criteria.OBSERVATION, Constants.Attributes.OBSERVATION_TYPE_ATTR)
            self._check_concept(c.value_as_concept, Constants.Criteria.OBSERVATION, Constants.Attributes.VALUE_AS_CONCEPT_ATTR)
            self._check_concept(c.qualifier, Constants.Criteria.OBSERVATION, Constants.Attributes.QUALIFIER_ATTR)
            self._check_concept(c.unit, Constants.Criteria.OBSERVATION, Constants.Attributes.UNIT_ATTR)
            self._check_concept(c.gender, Constants.Criteria.OBSERVATION, Constants.Attributes.GENDER_ATTR)
            self._check_concept(c.provider_specialty, Constants.Criteria.OBSERVATION, Constants.Attributes.PROVIDER_SPECIALITY_ATTR)
            self._check_concept(c.visit_type, Constants.Criteria.OBSERVATION, Constants.Attributes.VISIT_TYPE_ATTR)
        
        def check_observation_period(c: 'ObservationPeriod') -> None:
            self._check_concept(c.period_type, Constants.Criteria.OBSERVATION_PERIOD, Constants.Attributes.PERIOD_TYPE_ATTR)
        
        def check_procedure_occurrence(c: 'ProcedureOccurrence') -> None:
            self._check_concept(c.procedure_type, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.PROCEDURE_TYPE_ATTR)
            self._check_concept(c.modifier, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.MODIFIER_ATTR)
            self._check_concept(c.gender, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.GENDER_ATTR)
            self._check_concept(c.provider_specialty, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR)
            self._check_concept(c.visit_type, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.VISIT_TYPE_ATTR)
        
        def check_specimen(c: 'Specimen') -> None:
            self._check_concept(c.specimen_type, Constants.Criteria.SPECIMEN, Constants.Attributes.SPECIMEN_TYPE_ATTR)
            self._check_concept(c.unit, Constants.Criteria.SPECIMEN, Constants.Attributes.UNIT_ATTR)
            self._check_concept(c.anatomic_site, Constants.Criteria.SPECIMEN, Constants.Attributes.ANATOMIC_SITE_ATTR)
            self._check_concept(c.disease_status, Constants.Criteria.SPECIMEN, Constants.Attributes.DISEASE_STATUS_ATTR)
            self._check_concept(c.gender, Constants.Criteria.SPECIMEN, Constants.Attributes.GENDER_ATTR)
        
        def check_visit_occurrence(c: 'VisitOccurrence') -> None:
            self._check_concept(c.visit_type, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.VISIT_TYPE_ATTR)
            self._check_concept(c.gender, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.GENDER_ATTR)
            self._check_concept(c.provider_specialty, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR)
            self._check_concept(c.place_of_service, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.PLACE_OF_SERVICE_ATTR)
        
        def check_payer_plan_period(c: 'PayerPlanPeriod') -> None:
            self._check_concept(c.gender, Constants.Criteria.PAYER_PLAN_PERIOD, Constants.Attributes.GENDER_ATTR)
        
        def default_check(c: 'Criteria') -> None:
            pass  # No concept checks for this criteria type
        
        # Use isinstance checks to route to appropriate checker
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
        elif isinstance(criteria, ObservationPeriod):
            return check_observation_period
        elif isinstance(criteria, ProcedureOccurrence):
            return check_procedure_occurrence
        elif isinstance(criteria, Specimen):
            return check_specimen
        elif isinstance(criteria, VisitOccurrence):
            return check_visit_occurrence
        elif isinstance(criteria, PayerPlanPeriod):
            return check_payer_plan_period
        else:
            return default_check
    
    def _get_check_demographic(self, criteria: 'DemographicCriteria') -> Callable[['DemographicCriteria'], None]:
        """Get a checker function for demographic criteria.
        
        Args:
            criteria: The demographic criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        def check(c: 'DemographicCriteria') -> None:
            self._check_concept(c.ethnicity, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.ETHNICITY_ATTR)
            self._check_concept(c.gender, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.GENDER_ATTR)
            self._check_concept(c.race, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.RACE_ATTR)
        return check
    
    def _check_concept(self, concepts: Optional[List['Concept']], criteria_name: str, attribute: str) -> None:
        """Check if a concept array is empty.
        
        Args:
            concepts: The concept array to check
            criteria_name: The name of the criteria type
            attribute: The name of the attribute
        """
        def warning(template: str) -> None:
            self._reporter(template, self._group_name, criteria_name, attribute)
        
        Operations.match(concepts)\
            .when(lambda c: c is not None and len(c) == 0)\
            .then(lambda c: warning(self.WARNING_EMPTY_VALUE))

