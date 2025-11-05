"""
RangeCheck class.

This module provides validation for range values in criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Optional
from ..warning_severity import WarningSeverity
from .base_value_check import BaseValueCheck
from .warning_reporter import WarningReporter
from .range_checker_factory import RangeCheckerFactory

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import CorelatedCriteria
    from ...cohortdefinition.core import ObservationFilter, Window
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import CorelatedCriteria
        from ...cohortdefinition.core import ObservationFilter, Window


class RangeCheck(BaseValueCheck):
    """Check for invalid range values in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.RangeCheck
    """
    
    NEGATIVE_VALUE_ERROR = "Time window in criteria \"%s\" has negative value %d at %s"
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check range values in the expression.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        super()._check(expression, reporter)
        RangeCheckerFactory.get_factory(reporter, self.PRIMARY_CRITERIA).check(expression)
        
        if expression.primary_criteria:
            self._check_observation_filter(
                expression.primary_criteria.observation_window, 
                reporter, 
                "observation window"
            )
        
        RangeCheckerFactory.get_factory(reporter, self.PRIMARY_CRITERIA).check_range(
            expression.censor_window, "cohort", "censor window"
        )
    
    def _check_inclusion_rules(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check inclusion rules for window issues.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        super()._check_inclusion_rules(expression, reporter)
        
        if expression.inclusion_rules:
            for rule in expression.inclusion_rules:
                if rule.expression and rule.expression.criteria_list:
                    for criteria in rule.expression.criteria_list:
                        # Handle both dict and CorelatedCriteria objects
                        if isinstance(criteria, dict):
                            start_window = criteria.get('startWindow') or criteria.get('start_window')
                            end_window = criteria.get('endWindow') or criteria.get('end_window')
                        else:
                            start_window = getattr(criteria, 'start_window', None) or getattr(criteria, 'startWindow', None)
                            end_window = getattr(criteria, 'end_window', None) or getattr(criteria, 'endWindow', None)
                        self._check_window(start_window, reporter, rule.name)
                        self._check_window(end_window, reporter, rule.name)
    
    def _check_window(self, window, reporter: WarningReporter, name: str) -> None:
        """Check a window for negative values.
        
        Args:
            window: The window to check (Window object or dict)
            reporter: The warning reporter to use
            name: The name of the criteria
        """
        if window:
            # Handle dict windows
            if isinstance(window, dict):
                start = window.get('start') or window.get('Start')
                end = window.get('end') or window.get('End')
                
                if start:
                    start_days = start.get('days') if isinstance(start, dict) else getattr(start, 'days', None)
                    if start_days is not None and start_days < 0:
                        reporter(self.NEGATIVE_VALUE_ERROR, name, start_days, "start")
                
                if end:
                    end_days = end.get('days') if isinstance(end, dict) else getattr(end, 'days', None)
                    if end_days is not None and end_days < 0:
                        reporter(self.NEGATIVE_VALUE_ERROR, name, end_days, "end")
            else:
                # Window object
                if window.start and window.start.days is not None and window.start.days < 0:
                    reporter(self.NEGATIVE_VALUE_ERROR, name, window.start.days, "start")
                if window.end and window.end.days is not None and window.end.days < 0:
                    reporter(self.NEGATIVE_VALUE_ERROR, name, window.end.days, "end")
    
    def _check_observation_filter(
        self, 
        filter_val: Optional['ObservationFilter'], 
        reporter: WarningReporter, 
        name: str
    ) -> None:
        """Check an observation filter for negative values.
        
        Args:
            filter_val: The observation filter to check
            reporter: The warning reporter to use
            name: The name of the filter
        """
        if filter_val:
            if filter_val.prior_days < 0:
                reporter(self.NEGATIVE_VALUE_ERROR, name, filter_val.prior_days, "prior days")
            if filter_val.post_days < 0:
                reporter(self.NEGATIVE_VALUE_ERROR, name, filter_val.post_days, "post days")
    
    def _check_criteria(self, criteria, reporter: WarningReporter, name: str) -> None:
        """Check a corelated criteria for window issues.
        
        Args:
            criteria: The criteria to check (CorelatedCriteria or dict)
            reporter: The warning reporter to use
            name: The name of the criteria
        """
        super()._check_criteria(criteria, reporter, name)
        
        # Handle both dict and CorelatedCriteria objects
        if isinstance(criteria, dict):
            start_window = criteria.get('startWindow') or criteria.get('start_window')
            end_window = criteria.get('endWindow') or criteria.get('end_window')
        else:
            # CorelatedCriteria object
            start_window = getattr(criteria, 'start_window', None) or getattr(criteria, 'startWindow', None)
            end_window = getattr(criteria, 'end_window', None) or getattr(criteria, 'endWindow', None)
        
        self._check_window(start_window, reporter, name)
        self._check_window(end_window, reporter, name)
    
    def _get_factory(self, reporter: WarningReporter, name: str) -> RangeCheckerFactory:
        """Get a range checker factory.
        
        Args:
            reporter: The warning reporter to use
            name: The name of the criteria group
            
        Returns:
            A RangeCheckerFactory instance
        """
        return RangeCheckerFactory.get_factory(reporter, name)

