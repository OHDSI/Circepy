"""
Incomplete rule warning class for validation warnings.

This module provides warnings for incomplete inclusion rules.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from ..warning_severity import WarningSeverity
from .base_warning import BaseWarning


class IncompleteRuleWarning(BaseWarning):
    """Warning for incomplete inclusion rules.
    
    Java equivalent: org.ohdsi.circe.check.warnings.IncompleteRuleWarning
    
    This warning is raised when an inclusion rule is found to be incomplete
    or invalid.
    """
    
    INCOMPLETE_ERROR = "Incomplete rule %s."
    
    def __init__(self, severity: WarningSeverity, rule_name: str):
        """Initialize an incomplete rule warning.
        
        Args:
            severity: The severity level of this warning
            rule_name: The name of the incomplete rule
        """
        super().__init__(severity)
        self._rule_name = rule_name
    
    @property
    def rule_name(self) -> str:
        """Get the name of the incomplete rule.
        
        Returns:
            The rule name
        """
        return self._rule_name
    
    def to_message(self) -> str:
        """Generate the warning message.
        
        Returns:
            A formatted message string indicating which rule is incomplete
        """
        return self.INCOMPLETE_ERROR % self._rule_name

