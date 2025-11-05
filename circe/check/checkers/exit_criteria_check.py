"""
ExitCriteriaCheck class.

This module provides validation for exit criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .base_check import BaseCheck
from .warning_reporter import WarningReporter
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.core import CustomEraStrategy
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.core import CustomEraStrategy


class ExitCriteriaCheck(BaseCheck):
    """Check for missing drug concept set in exit criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.ExitCriteriaCheck
    """
    
    DRUG_CONCEPT_EMPTY_ERROR = "Drug concept set must be selected at Exit Criteria."
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check exit criteria for missing drug concept set.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        match_result = Operations.match(expression.end_strategy)
        match_result.is_a(CustomEraStrategy)
        match_result.then(lambda s: Operations.match(s)
                .when(lambda ces: ces.drug_codeset_id is None)
                .then(lambda ces: reporter(self.DRUG_CONCEPT_EMPTY_ERROR))
            )

