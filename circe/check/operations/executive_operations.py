"""
ExecutiveOperations interface for pattern matching.

This module provides the ExecutiveOperations interface for executing
operations in pattern matching chains.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Protocol, TypeVar, Generic, Callable

T = TypeVar('T')
V = TypeVar('V')
from .execution import Execution
from .conditional_operations import ConditionalOperations


class ExecutiveOperations(Protocol, Generic[T, V]):
    """Interface for executive operations in pattern matching.
    
    Java equivalent: org.ohdsi.circe.check.operations.ExecutiveOperations
    
    This interface provides methods for executing operations when
    pattern matching conditions are met.
    """
    
    def then(self, consumer: Callable[[T], None]) -> ConditionalOperations[T, V]:
        """Execute a consumer function if the condition was met.
        
        Args:
            consumer: The function to execute
            
        Returns:
            A ConditionalOperations instance for chaining
        """
        ...
    
    def then(self, execution: Execution) -> ConditionalOperations[T, V]:
        """Execute an Execution if the condition was met.
        
        Args:
            execution: The Execution to execute
            
        Returns:
            A ConditionalOperations instance for chaining
        """
        ...
    
    def then_return(self, function: Callable[[T], V]) -> ConditionalOperations[T, V]:
        """Execute a function and return its value if the condition was met.
        
        Args:
            function: The function to execute and return its result
            
        Returns:
            A ConditionalOperations instance for chaining
        """
        ...

