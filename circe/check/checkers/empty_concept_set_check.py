"""
EmptyConceptSetCheck class.

This module provides validation for empty concept sets.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .base_check import BaseCheck
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression


class EmptyConceptSetCheck(BaseCheck):
    """Check for empty concept sets.
    
    Java equivalent: org.ohdsi.circe.check.checkers.EmptyConceptSetCheck
    """
    
    EMPTY_ERROR = "Concept set %s contains no concepts"
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check for empty concept sets.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        if expression.concept_sets:
            for concept_set in expression.concept_sets:
                if (not concept_set.expression or
                    not concept_set.expression.items or
                    len(concept_set.expression.items) == 0):
                    reporter(self.EMPTY_ERROR, concept_set.name)

