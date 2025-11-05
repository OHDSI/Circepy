"""
Execution interface for deferred execution.

This module provides the Execution interface for deferred execution
of operations, similar to Java's functional interface.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Protocol


class Execution(Protocol):
    """Functional interface for deferred execution.
    
    Java equivalent: org.ohdsi.circe.check.operations.Execution
    
    This interface represents an operation that can be executed later.
    """
    
    def apply(self) -> None:
        """Execute the operation."""
        ...

