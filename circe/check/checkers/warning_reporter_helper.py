"""
WarningReporterHelper utility class.

This module provides a helper class for creating warning reporters
with pre-configured templates and group names.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..operations.execution import Execution
from .warning_reporter import WarningReporter


class WarningReporterHelper:
    """Helper class for creating warning reporters with templates.
    
    Java equivalent: org.ohdsi.circe.check.checkers.WarningReporterHelper
    
    This class helps create Execution objects that can be used to
    add warnings with consistent formatting.
    """
    
    def __init__(self, reporter: WarningReporter, template: str, primary_group: str):
        """Initialize a warning reporter helper.
        
        Args:
            reporter: The warning reporter to use
            template: The message template string
            primary_group: The primary group name for the warning
        """
        self._reporter = reporter
        self._template = template
        self._primary_group = primary_group
    
    def add_warning(self, secondary_group: str) -> Execution:
        """Create an Execution that adds a warning.
        
        Args:
            secondary_group: The secondary group name for the warning
            
        Returns:
            An Execution object that will add the warning when called
        """
        def exec_warning(_value=None) -> None:
            # Accept optional value parameter (unused) for compatibility with Operations.then()
            self._reporter(self._template, self._primary_group, secondary_group)
        
        return exec_warning

