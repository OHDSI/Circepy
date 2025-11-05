"""
Base check class for validation checks.

This module provides the base class for all validation checks.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Any
from ..check import Check
from ..warning import Warning
from ..warning_severity import WarningSeverity
from ..warnings.default_warning import DefaultWarning
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression


class BaseCheck(Check):
    """Base class for all validation checks.
    
    Java equivalent: org.ohdsi.circe.check.checkers.BaseCheck
    
    This class provides common functionality for all checks, including
    severity management and warning reporting.
    """
    
    INCLUSION_RULE = "inclusion rule "
    ADDITIONAL_RULE = "additional rule"
    INITIAL_EVENT = "initial event"
    
    def check(self, expression: 'CohortExpression') -> List[Warning]:
        """Check a cohort expression and return warnings.
        
        This is the main entry point that sets up the warning reporter
        and calls the abstract check method.
        
        Args:
            expression: The cohort expression to validate
            
        Returns:
            A list of warnings found during validation
        """
        warnings: List[Warning] = []
        self._check(expression, self._define_reporter(warnings))
        return warnings
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Internal check method to be implemented by subclasses.
        
        Args:
            expression: The cohort expression to validate
            reporter: The warning reporter to use for adding warnings
        """
        raise NotImplementedError("Subclasses must implement _check")
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for warnings from this check.
        
        Returns:
            The default severity level (CRITICAL by default)
        """
        return WarningSeverity.CRITICAL
    
    def _define_reporter(self, warnings: List[Warning]) -> WarningReporter:
        """Define the warning reporter for this check.
        
        Args:
            warnings: The list to which warnings will be added
            
        Returns:
            A WarningReporter that adds warnings to the list
        """
        return self._get_reporter(self._define_severity(), warnings)
    
    def _get_reporter(self, severity: WarningSeverity, warnings: List[Warning]) -> WarningReporter:
        """Get a warning reporter for the given severity level.
        
        Args:
            severity: The severity level for warnings
            warnings: The list to which warnings will be added
            
        Returns:
            A WarningReporter that creates DefaultWarning instances
        """
        def reporter(template: str, *args: Any) -> None:
            message = template % args if args else template
            warnings.append(DefaultWarning(severity, message))
        
        return reporter

