"""
ConceptSetCriteriaCheck class.

This module provides validation for concept sets in criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning_severity import WarningSeverity
from ..operations.operations import Operations
from ..utils.criteria_name_helper import CriteriaNameHelper
from .base_criteria_check import BaseCriteriaCheck
from .warning_reporter import WarningReporter
from .warning_reporter_helper import WarningReporterHelper

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.criteria import (
        Criteria, ConditionEra, ConditionOccurrence, Death, DeviceExposure,
        DoseEra, DrugEra, DrugExposure, Measurement, Observation,
        ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail
    )
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import (
            Criteria, ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail
        )


class ConceptSetCriteriaCheck(BaseCriteriaCheck):
    """Check for missing concept sets in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.ConceptSetCriteriaCheck
    """
    
    NO_CONCEPT_SET_ERROR = "No concept set specified as part of a criteria at %s in %s criteria"
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _check_criteria(self, criteria: 'Criteria', group_name: str, reporter: WarningReporter) -> None:
        """Check if a criteria has a concept set specified.
        
        Args:
            criteria: The criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        helper = WarningReporterHelper(reporter, self.NO_CONCEPT_SET_ERROR, group_name)
        criteria_name = CriteriaNameHelper.get_criteria_name(criteria)
        add_warning = helper.add_warning(criteria_name)
        
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail
        )
        
        Operations.match(criteria)\
            .is_a(ConditionEra)\
            .then(lambda c: Operations.match(c)
                .when(lambda ce: ce.codeset_id is None)
                .then(add_warning)
            )\
            .is_a(ConditionOccurrence)\
            .then(lambda c: Operations.match(c)
                .when(lambda co: co.codeset_id is None and co.condition_source_concept is None)
                .then(add_warning)
            )\
            .is_a(Death)\
            .then(lambda c: Operations.match(c)
                .when(lambda d: d.codeset_id is None)
                .then(add_warning)
            )\
            .is_a(DeviceExposure)\
            .then(lambda c: Operations.match(c)
                .when(lambda de: de.codeset_id is None and de.device_source_concept is None)
                .then(add_warning)
            )\
            .is_a(DoseEra)\
            .then(lambda c: Operations.match(c)
                .when(lambda de: de.codeset_id is None)
                .then(add_warning)
            )\
            .is_a(DrugEra)\
            .then(lambda c: Operations.match(c)
                .when(lambda de: de.codeset_id is None)
                .then(add_warning)
            )\
            .is_a(DrugExposure)\
            .then(lambda c: Operations.match(c)
                .when(lambda de: de.codeset_id is None and de.drug_source_concept is None)
                .then(add_warning)
            )\
            .is_a(Measurement)\
            .then(lambda c: Operations.match(c)
                .when(lambda m: m.codeset_id is None and m.measurement_source_concept is None)
                .then(add_warning)
            )\
            .is_a(Observation)\
            .then(lambda c: Operations.match(c)
                .when(lambda o: o.codeset_id is None and o.observation_source_concept is None)
                .then(add_warning)
            )\
            .is_a(ProcedureOccurrence)\
            .then(lambda c: Operations.match(c)
                .when(lambda po: po.codeset_id is None and po.procedure_source_concept is None)
                .then(add_warning)
            )\
            .is_a(Specimen)\
            .then(lambda c: Operations.match(c)
                .when(lambda s: s.codeset_id is None and s.specimen_source_concept is None)
                .then(add_warning)
            )\
            .is_a(VisitOccurrence)\
            .then(lambda c: Operations.match(c)
                .when(lambda vo: vo.codeset_id is None and vo.visit_source_concept is None)
                .then(add_warning)
            )\
            .is_a(VisitDetail)\
            .then(lambda c: Operations.match(c)
                .when(lambda vd: vd.codeset_id is None and vd.visit_detail_source_concept is None)
                .then(add_warning)
            )

