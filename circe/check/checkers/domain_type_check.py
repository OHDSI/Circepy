"""
DomainTypeCheck class.

This module provides validation for missing domain type specifications.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List
from ..warning_severity import WarningSeverity
from ..utils.criteria_name_helper import CriteriaNameHelper
from ..operations.execution import Execution
from .base_criteria_check import BaseCriteriaCheck
from .warning_reporter import WarningReporter
from .warning_reporter_helper import WarningReporterHelper
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import (
        Criteria, ConditionOccurrence, Death, DeviceExposure,
        DrugExposure, Measurement, Observation, ProcedureOccurrence,
        Specimen, VisitOccurrence, VisitDetail
    )
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import (
            Criteria, ConditionOccurrence, Death, DeviceExposure,
            DrugExposure, Measurement, Observation, ProcedureOccurrence,
            Specimen, VisitOccurrence, VisitDetail
        )


class DomainTypeCheck(BaseCriteriaCheck):
    """Check for missing domain type specifications.
    
    Java equivalent: org.ohdsi.circe.check.checkers.DomainTypeCheck
    """
    
    WARNING = "It's not specified what type of records to look for in %s"
    
    def __init__(self):
        """Initialize the domain type check."""
        super().__init__()
        self._warn_names: List[str] = []
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            INFO severity level
        """
        return WarningSeverity.INFO
    
    def _check_criteria(self, criteria: 'Criteria', group_name: str, reporter: WarningReporter) -> None:
        """Check if a criteria has a domain type specified.
        
        Args:
            criteria: The criteria to check
            group_name: The name of the group containing this criteria
            reporter: The warning reporter to use
        """
        name = CriteriaNameHelper.get_criteria_name(criteria)
        
        def add_warning() -> None:
            self._warn_names.append(f"{name} at {group_name}")
        
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionOccurrence, Death, DeviceExposure, DrugExposure,
            Measurement, Observation, ProcedureOccurrence, Specimen,
            VisitOccurrence, VisitDetail
        )
        
        Operations.match(criteria)\
            .is_a(ConditionOccurrence)\
            .then(lambda c: Operations.match(c)
                .when(lambda co: co.condition_type is None)
                .then(lambda co: add_warning())
            )\
            .is_a(Death)\
            .then(lambda c: Operations.match(c)
                .when(lambda d: d.death_type is None)
                .then(lambda d: add_warning())
            )\
            .is_a(DeviceExposure)\
            .then(lambda c: Operations.match(c)
                .when(lambda de: de.device_type is None)
                .then(lambda de: add_warning())
            )\
            .is_a(DrugExposure)\
            .then(lambda c: Operations.match(c)
                .when(lambda de: de.drug_type is None)
                .then(lambda de: add_warning())
            )\
            .is_a(Measurement)\
            .then(lambda c: Operations.match(c)
                .when(lambda m: m.measurement_type is None)
                .then(lambda m: add_warning())
            )\
            .is_a(Observation)\
            .then(lambda c: Operations.match(c)
                .when(lambda o: o.observation_type is None)
                .then(lambda o: add_warning())
            )\
            .is_a(ProcedureOccurrence)\
            .then(lambda c: Operations.match(c)
                .when(lambda po: po.procedure_type is None)
                .then(lambda po: add_warning())
            )\
            .is_a(Specimen)\
            .then(lambda c: Operations.match(c)
                .when(lambda s: s.specimen_type is None)
                .then(lambda s: add_warning())
            )\
            .is_a(VisitOccurrence)\
            .then(lambda c: Operations.match(c)
                .when(lambda vo: vo.visit_type is None)
                .then(lambda vo: add_warning())
            )\
            .is_a(VisitDetail)\
            .then(lambda c: Operations.match(c)
                .when(lambda vd: vd.visit_detail_type_cs is None)
                .then(lambda vd: add_warning())
            )
    
    def _after_check(self, reporter: WarningReporter, expression: 'CohortExpression') -> None:
        """Report warnings after all criteria have been checked.
        
        Args:
            reporter: The warning reporter to use
            expression: The cohort expression that was checked
        """
        if self._warn_names:
            names = ", ".join(self._warn_names)
            reporter(self.WARNING, names)

