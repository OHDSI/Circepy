"""
IncompleteRuleCheck class.

This module provides validation for incomplete inclusion rules.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List
from ..warning import Warning
from ..warning_severity import WarningSeverity
from ..warnings.incomplete_rule_warning import IncompleteRuleWarning
from .base_check import BaseCheck
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import InclusionRule
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import InclusionRule


class IncompleteRuleCheck(BaseCheck):
    """Check for incomplete inclusion rules.
    
    Java equivalent: org.ohdsi.circe.check.checkers.IncompleteRuleCheck
    """
    
    def _get_reporter(self, severity: WarningSeverity, warnings: List[Warning]) -> WarningReporter:
        """Get a warning reporter that creates IncompleteRuleWarning instances.
        
        Args:
            severity: The severity level
            warnings: The list to add warnings to
            
        Returns:
            A WarningReporter that creates IncompleteRuleWarning instances
        """
        def reporter(name: str, *args) -> None:
            warnings.append(IncompleteRuleWarning(severity, name))
        return reporter
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check for incomplete inclusion rules.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        if expression.inclusion_rules:
            for rule in expression.inclusion_rules:
                self._check_inclusion_rule(rule, reporter)
    
    def _check_inclusion_rule(self, rule: 'InclusionRule', reporter: WarningReporter) -> None:
        """Check if an inclusion rule is incomplete.
        
        Args:
            rule: The inclusion rule to check
            reporter: The warning reporter to use
        """
        # Check if expression is empty
        if not rule.expression or (
            (not hasattr(rule.expression, 'criteria_list') or not rule.expression.criteria_list) and
            (not hasattr(rule.expression, 'demographic_criteria_list') or not rule.expression.demographic_criteria_list) and
            (not hasattr(rule.expression, 'groups') or not rule.expression.groups)
        ):
            reporter(rule.name)

