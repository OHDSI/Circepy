"""
CriteriaNameHelper utility class.

This module provides a utility class for getting human-readable names
for criteria types.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..constants import Constants
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.criteria import (
        ConditionEra, ConditionOccurrence, Death, DeviceExposure,
        DoseEra, DrugEra, DrugExposure, Measurement, Observation,
        ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail,
        ObservationPeriod, PayerPlanPeriod, LocationRegion
    )
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail,
            ObservationPeriod, PayerPlanPeriod, LocationRegion
        )


class CriteriaNameHelper:
    """Helper class for getting criteria type names.
    
    Java equivalent: org.ohdsi.circe.check.utils.CriteriaNameHelper
    
    This class provides a method to get human-readable names for
    different criteria types.
    """
    
    @staticmethod
    def get_criteria_name(criteria) -> str:
        """Get the human-readable name for a criteria type.
        
        Args:
            criteria: The criteria instance to get the name for
            
        Returns:
            A string name for the criteria type
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail,
            ObservationPeriod, PayerPlanPeriod, LocationRegion
        )
        
        return Operations.match(criteria)\
            .is_a(ConditionEra)\
            .then_return(lambda c: Constants.Criteria.CONDITION_ERA)\
            .is_a(ConditionOccurrence)\
            .then_return(lambda c: Constants.Criteria.CONDITION_OCCURRENCE)\
            .is_a(Death)\
            .then_return(lambda c: Constants.Criteria.DEATH)\
            .is_a(DeviceExposure)\
            .then_return(lambda c: Constants.Criteria.DEVICE_EXPOSURE)\
            .is_a(DoseEra)\
            .then_return(lambda c: Constants.Criteria.DOSE_ERA)\
            .is_a(DrugEra)\
            .then_return(lambda c: Constants.Criteria.DRUG_ERA)\
            .is_a(DrugExposure)\
            .then_return(lambda c: Constants.Criteria.DRUG_EXPOSURE)\
            .is_a(Measurement)\
            .then_return(lambda c: Constants.Criteria.MEASUREMENT)\
            .is_a(Observation)\
            .then_return(lambda c: Constants.Criteria.OBSERVATION)\
            .is_a(ObservationPeriod)\
            .then_return(lambda c: Constants.Criteria.OBSERVATION_PERIOD)\
            .is_a(ProcedureOccurrence)\
            .then_return(lambda c: Constants.Criteria.PROCEDURE_OCCURRENCE)\
            .is_a(Specimen)\
            .then_return(lambda c: Constants.Criteria.SPECIMEN)\
            .is_a(VisitOccurrence)\
            .then_return(lambda c: Constants.Criteria.VISIT_OCCURRENCE)\
            .is_a(VisitDetail)\
            .then_return(lambda c: Constants.Criteria.VISIT_DETAIL)\
            .is_a(PayerPlanPeriod)\
            .then_return(lambda c: Constants.Criteria.PAYER_PLAN_PERIOD)\
            .value() or "unknown criteria"

