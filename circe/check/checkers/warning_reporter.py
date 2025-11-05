"""
WarningReporter interface for validation checks.

This module defines the functional interface for reporting warnings during
validation checks.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Protocol, Any


class WarningReporter(Protocol):
    """Functional interface for reporting warnings.
    
    Java equivalent: org.ohdsi.circe.check.checkers.WarningReporter
    
    This is a callable interface that accepts a template string and
    variable arguments to format and add warnings.
    """
    
    def __call__(self, template: str, *args: Any) -> None:
        """Add a warning using a template string and arguments.
        
        Args:
            template: A format string template (e.g., "Error in %s: %s")
            *args: Arguments to format into the template
        """
        ...

