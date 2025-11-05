"""
Check interface for validation checks.

This module defines the base interface for validation checks that can be
run against cohort expressions.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING
from .warning import Warning

if TYPE_CHECKING:
    from ..cohortdefinition.cohort import CohortExpression
else:
    # Import at runtime to avoid circular dependencies
    try:
        from ..cohortdefinition.cohort import CohortExpression
    except ImportError:
        pass


class Check(ABC):
    """Base interface for validation checks.
    
    Java equivalent: org.ohdsi.circe.check.Check
    
    All validation checks must implement this interface and provide
    a method to check a cohort expression and return warnings.
    """
    
    @abstractmethod
    def check(self, expression: 'CohortExpression') -> List[Warning]:
        """Check a cohort expression and return any warnings.
        
        Args:
            expression: The cohort expression to validate
            
        Returns:
            A list of warnings found during validation. Empty list if no issues.
        """
        pass

