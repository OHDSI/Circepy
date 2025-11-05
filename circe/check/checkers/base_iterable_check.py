"""
Base iterable check class for validation checks.

This module provides the base class for checks that iterate over
cohort expression elements.

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


class BaseIterableCheck(BaseCheck):
    """Base class for checks that iterate over expression elements.
    
    Java equivalent: org.ohdsi.circe.check.checkers.BaseIterableCheck
    
    This class provides hooks for before/after check processing and
    delegates to an internal check method.
    """
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check implementation that calls hooks and internal check.
        
        Args:
            expression: The cohort expression to validate
            reporter: The warning reporter to use
        """
        self._before_check(reporter, expression)
        self._internal_check(expression, reporter)
        self._after_check(reporter, expression)
    
    def _before_check(self, reporter: WarningReporter, expression: 'CohortExpression') -> None:
        """Hook called before the internal check runs.
        
        Args:
            reporter: The warning reporter
            expression: The cohort expression being validated
        """
        pass
    
    def _after_check(self, reporter: WarningReporter, expression: 'CohortExpression') -> None:
        """Hook called after the internal check runs.
        
        Args:
            reporter: The warning reporter
            expression: The cohort expression being validated
        """
        pass
    
    def _internal_check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Internal check method to be implemented by subclasses.
        
        Args:
            expression: The cohort expression to validate
            reporter: The warning reporter to use
        """
        raise NotImplementedError("Subclasses must implement _internal_check")

