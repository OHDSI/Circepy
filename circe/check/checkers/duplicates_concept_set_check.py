"""
DuplicatesConceptSetCheck class.

This module provides validation for duplicate concept sets.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import TYPE_CHECKING
from ..warning_severity import WarningSeverity
from .base_check import BaseCheck
from .warning_reporter import WarningReporter
from .comparisons import Comparisons

if TYPE_CHECKING:
    from ...cohortdefinition.cohort import CohortExpression
    from ...vocabulary.concept import ConceptSet
else:
    # Import at runtime to avoid circular dependencies
    try:
        from ...cohortdefinition.cohort import CohortExpression
        from ...vocabulary.concept import ConceptSet
    except ImportError:
        pass


class DuplicatesConceptSetCheck(BaseCheck):
    """Check for duplicate concept sets.
    
    Java equivalent: org.ohdsi.circe.check.checkers.DuplicatesConceptSetCheck
    """
    
    DUPLICATES_WARNING = "Concept set %s contains the same concepts like %s"
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check for duplicate concept sets.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        if expression.concept_sets and len(expression.concept_sets) > 1:
            size = len(expression.concept_sets)
            for i in range(size - 1):
                concept_set = expression.concept_sets[i]
                # Create comparison function for this concept set
                compare_func = Comparisons.compare_concept_set(concept_set)
                duplicates = [
                    cs for cs in expression.concept_sets[i + 1:]
                    if compare_func(cs)
                ]
                if duplicates:
                    names = ", ".join(cs.name for cs in duplicates)
                    reporter(self.DUPLICATES_WARNING, concept_set.name, names)

