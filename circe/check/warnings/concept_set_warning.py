"""
Concept set warning class for validation warnings.

This module provides warnings related to concept sets.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Optional
from ..warning_severity import WarningSeverity
from .base_warning import BaseWarning
from ...vocabulary.concept import ConceptSet


class ConceptSetWarning(BaseWarning):
    """Warning related to a specific concept set.
    
    Java equivalent: org.ohdsi.circe.check.warnings.ConceptSetWarning
    
    This warning type includes a reference to the concept set that
    triggered the warning, allowing for more detailed error reporting.
    """
    
    def __init__(self, severity: WarningSeverity, template: str, concept_set: Optional[ConceptSet]):
        """Initialize a concept set warning.
        
        Args:
            severity: The severity level of this warning
            template: Message template string (should contain %s for concept set name)
            concept_set: The concept set that triggered this warning
        """
        super().__init__(severity)
        self._template = template
        self._concept_set = concept_set
    
    @property
    def concept_set(self) -> Optional[ConceptSet]:
        """Get the concept set associated with this warning.
        
        Returns:
            The concept set, or None if not available
        """
        return self._concept_set
    
    @property
    def concept_set_id(self) -> int:
        """Get the concept set ID.
        
        Returns:
            The concept set ID, or 0 if concept set is None
        """
        return self._concept_set.id if self._concept_set is not None else 0
    
    def to_message(self) -> str:
        """Generate the warning message.
        
        Returns:
            A formatted message string using the template and concept set name
        """
        if self._concept_set is not None:
            return self._template % self._concept_set.name
        else:
            return self._template % "Unknown"

