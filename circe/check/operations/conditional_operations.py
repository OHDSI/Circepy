"""
ConditionalOperations interface for pattern matching.

This module provides the ConditionalOperations interface for pattern
matching operations with conditional execution.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Protocol, TypeVar, Generic, Callable, Any

T = TypeVar('T')
V = TypeVar('V')


class ConditionalOperations(Protocol, Generic[T, V]):
    """Interface for conditional operations in pattern matching.
    
    Java equivalent: org.ohdsi.circe.check.operations.ConditionalOperations
    
    This interface provides methods for conditional execution based on
    pattern matching results.
    """
    
    def when(self, condition: Callable[[T], bool]) -> 'ExecutiveOperations[T, V]':
        """Apply a condition to the value.
        
        Args:
            condition: A function that returns True if the condition matches
            
        Returns:
            An ExecutiveOperations instance for chaining
        """
        ...
    
    def is_a(self, clazz: type) -> 'ExecutiveOperations[T, V]':
        """Check if the value is an instance of the given class.
        
        Args:
            clazz: The class to check against
            
        Returns:
            An ExecutiveOperations instance for chaining
        """
        ...
    
    def or_else(self, consumer: Callable[[T], None]) -> None:
        """Execute if the condition was not met.
        
        Args:
            consumer: The function to execute if condition was not met
        """
        ...
    
    def value(self) -> V:
        """Get the return value from then_return operations.
        
        Returns:
            The value returned by a then_return operation, or None
        """
        ...

