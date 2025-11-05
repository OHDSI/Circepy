"""
TextCheck class.

This module provides validation for TextFilter fields in criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning_severity import WarningSeverity
from .base_value_check import BaseValueCheck
from .warning_reporter import WarningReporter
from .text_checker_factory import TextCheckerFactory


class TextCheck(BaseValueCheck):
    """Check for empty TextFilter values in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.TextCheck
    """
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _get_factory(self, reporter: WarningReporter, name: str) -> TextCheckerFactory:
        """Get a text checker factory.
        
        Args:
            reporter: The warning reporter to use
            name: The name of the criteria group
            
        Returns:
            A TextCheckerFactory instance
        """
        return TextCheckerFactory.get_factory(reporter, name)

