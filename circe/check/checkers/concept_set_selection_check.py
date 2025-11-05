"""
ConceptSetSelectionCheck class.

This module provides validation for ConceptSetSelection in criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .base_value_check import BaseValueCheck
from .warning_reporter import WarningReporter
from .concept_set_selection_checker_factory import ConceptSetSelectionCheckerFactory


class ConceptSetSelectionCheck(BaseValueCheck):
    """Check for empty ConceptSetSelection values in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.ConceptSetSelectionCheck
    """
    
    def _get_factory(self, reporter: WarningReporter, name: str) -> ConceptSetSelectionCheckerFactory:
        """Get a concept set selection checker factory.
        
        Args:
            reporter: The warning reporter to use
            name: The name of the criteria group
            
        Returns:
            A ConceptSetSelectionCheckerFactory instance
        """
        return ConceptSetSelectionCheckerFactory.get_factory(reporter, name)

