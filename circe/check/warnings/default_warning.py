"""
Default warning class for validation warnings.

This module provides the default warning implementation for simple
text-based warnings.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning_severity import WarningSeverity
from .base_warning import BaseWarning


class DefaultWarning(BaseWarning):
    """Default warning implementation with a simple message.
    
    Java equivalent: org.ohdsi.circe.check.warnings.DefaultWarning
    
    This is the most common warning type, containing a severity level
    and a message string.
    """
    
    def __init__(self, severity: WarningSeverity, message: str):
        """Initialize a default warning.
        
        Args:
            severity: The severity level of this warning
            message: The warning message text
        """
        super().__init__(severity)
        self._message = message
    
    def to_message(self) -> str:
        """Get the warning message.
        
        Returns:
            The warning message text
        """
        return self._message

