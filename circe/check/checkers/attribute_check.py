"""
AttributeCheck class.

This module provides validation for attributes in demographic criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning_severity import WarningSeverity
from .base_value_check import BaseValueCheck
from .warning_reporter import WarningReporter
from .attribute_checker_factory import AttributeCheckerFactory


class AttributeCheck(BaseValueCheck):
    """Check for missing attributes in demographic criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.AttributeCheck
    """
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _get_factory(self, reporter: WarningReporter, name: str) -> AttributeCheckerFactory:
        """Get an attribute checker factory.
        
        Args:
            reporter: The warning reporter to use
            name: The name of the criteria group
            
        Returns:
            An AttributeCheckerFactory instance
        """
        return AttributeCheckerFactory.get_factory(reporter, name)

