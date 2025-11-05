"""
DrugDomainCheck class.

This module provides validation for drug domain concept sets.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional
from ..warning_severity import WarningSeverity
from .base_check import BaseCheck
from .warning_reporter import WarningReporter
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import Criteria
    from ...cohortdefinition.core import CustomEraStrategy
    from ...vocabulary.concept import ConceptSet
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import Criteria
        from ...cohortdefinition.core import CustomEraStrategy
        from ...vocabulary.concept import ConceptSet


class DrugDomainCheck(BaseCheck):
    """Check for drug domain concept sets not used in exit criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.DrugDomainCheck
    """
    
    MESSAGE = "%s %s used in initial event and not used for cohort exit criteria"
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            INFO severity level
        """
        return WarningSeverity.INFO
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check for drug domain concept sets.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        if not expression.primary_criteria or not expression.primary_criteria.criteria_list:
            return
        
        concept_sets: List['ConceptSet'] = []
        
        # Map criteria to codeset IDs
        codeset_ids = [
            self._map_criteria(criteria) 
            for criteria in expression.primary_criteria.criteria_list
        ]
        
        # Filter to only drug domain concept sets
        for codeset_id in codeset_ids:
            if codeset_id and self._is_concept_in_drug_domain(expression, codeset_id):
                concept_set = self._map_concept_set(expression, codeset_id)
                if concept_set:
                    concept_sets.append(concept_set)
        
        # Filter out concept sets used in exit strategy
        if isinstance(expression.end_strategy, CustomEraStrategy):
            concept_sets = [
                cs for cs in concept_sets 
                if cs.id != expression.end_strategy.drug_codeset_id
            ]
        
        if concept_sets:
            names = ", ".join(cs.name for cs in concept_sets)
            title = "Concept sets" if len(concept_sets) > 1 else "Concept set"
            reporter(self.MESSAGE, title, names)
    
    def _map_criteria(self, criteria: 'Criteria') -> Optional[int]:
        """Map a criteria to its codeset ID.
        
        Args:
            criteria: The criteria to map
            
        Returns:
            The codeset ID, or None
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail
        )
        
        return Operations.match(criteria)\
            .is_a(ConditionEra).then_return(lambda c: c.codeset_id)\
            .is_a(ConditionOccurrence).then_return(lambda c: c.codeset_id)\
            .is_a(Death).then_return(lambda c: c.codeset_id)\
            .is_a(DeviceExposure).then_return(lambda c: c.codeset_id)\
            .is_a(DoseEra).then_return(lambda c: c.codeset_id)\
            .is_a(DrugEra).then_return(lambda c: c.codeset_id)\
            .is_a(DrugExposure).then_return(lambda c: c.codeset_id)\
            .is_a(Measurement).then_return(lambda c: c.codeset_id)\
            .is_a(Observation).then_return(lambda c: c.codeset_id)\
            .is_a(ProcedureOccurrence).then_return(lambda c: c.codeset_id)\
            .is_a(Specimen).then_return(lambda c: c.codeset_id)\
            .is_a(VisitOccurrence).then_return(lambda c: c.codeset_id)\
            .is_a(VisitDetail).then_return(lambda c: c.codeset_id)\
            .value()
    
    def _is_concept_in_drug_domain(self, expression: 'CohortExpression', codeset_id: int) -> bool:
        """Check if a concept set contains drug domain concepts.
        
        Args:
            expression: The cohort expression
            codeset_id: The codeset ID to check
            
        Returns:
            True if the concept set contains drug domain concepts, False otherwise
        """
        if not expression.concept_sets:
            return False
        
        concept_set = next((cs for cs in expression.concept_sets if cs.id == codeset_id), None)
        if not concept_set or not concept_set.expression or not concept_set.expression.items:
            return False
        
        return any(
            item.concept and item.concept.domain_id and item.concept.domain_id.upper() == "DRUG"
            for item in concept_set.expression.items
        )
    
    def _map_concept_set(self, expression: 'CohortExpression', codeset_id: int) -> Optional['ConceptSet']:
        """Map a codeset ID to a concept set.
        
        Args:
            expression: The cohort expression
            codeset_id: The codeset ID to map
            
        Returns:
            The concept set, or None
        """
        if not expression.concept_sets:
            return None
        return next((cs for cs in expression.concept_sets if cs.id == codeset_id), None)

