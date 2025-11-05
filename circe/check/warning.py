"""
Warning interface for validation checks.

This module defines the base interface for warnings generated during
cohort expression validation.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from abc import ABC, abstractmethod
from typing import Protocol


class Warning(ABC):
    """Base interface for validation warnings.
    
    Java equivalent: org.ohdsi.circe.check.Warning
    
    All warnings must implement this interface and provide a message
    that describes the validation issue.
    """
    
    @abstractmethod
    def to_message(self) -> str:
        """Generate a human-readable message describing the warning.
        
        Returns:
            A string message describing the validation issue.
        """
        pass

