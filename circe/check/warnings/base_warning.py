"""
Base warning class for validation warnings.

This module provides the base class for all validation warnings.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning import Warning
from ..warning_severity import WarningSeverity


class BaseWarning(Warning):
    """Base class for all validation warnings.
    
    Java equivalent: org.ohdsi.circe.check.warnings.BaseWarning
    
    All warning classes should extend this base class to provide
    common functionality like severity tracking.
    """
    
    def __init__(self, severity: WarningSeverity):
        """Initialize a warning with a severity level.
        
        Args:
            severity: The severity level of this warning
        """
        self._severity = severity
    
    @property
    def severity(self) -> WarningSeverity:
        """Get the severity level of this warning.
        
        Returns:
            The warning severity level
        """
        return self._severity

