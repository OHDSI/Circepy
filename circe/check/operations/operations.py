"""
Operations class for pattern matching.

This module provides the Operations class that implements pattern matching
functionality similar to Java's pattern matching.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import TypeVar, Generic, Callable, Any, Optional
from .execution import Execution
from .conditional_operations import ConditionalOperations
from .executive_operations import ExecutiveOperations

T = TypeVar('T')
V = TypeVar('V')


class Operations(Generic[T, V], ConditionalOperations[T, V], ExecutiveOperations[T, V]):
    """Pattern matching operations class.
    
    Java equivalent: org.ohdsi.circe.check.operations.Operations
    
    This class provides a fluent interface for pattern matching and
    conditional execution, similar to Java's pattern matching.
    """
    
    def __init__(self, value: T):
        """Initialize operations with a value.
        
        Args:
            value: The value to match against
        """
        self._value = value
        self._result: Optional[bool] = None
        self._return_value: Optional[V] = None
    
    @staticmethod
    def match(value: T) -> ConditionalOperations[T, V]:
        """Create a new Operations instance for pattern matching.
        
        Args:
            value: The value to match against
            
        Returns:
            A ConditionalOperations instance for chaining
        """
        return Operations(value)
    
    def when(self, condition: Callable[[T], bool]) -> ExecutiveOperations[T, V]:
        """Apply a condition to the value.
        
        Args:
            condition: A function that returns True if the condition matches
            
        Returns:
            An ExecutiveOperations instance for chaining
        """
        self._result = self._value is not None and condition(self._value)
        return self
    
    def is_a(self, clazz: type) -> ExecutiveOperations[T, V]:
        """Check if the value is an instance of the given class.
        
        Args:
            clazz: The class to check against
            
        Returns:
            An ExecutiveOperations instance for chaining
        """
        self._result = (
            clazz is not None and
            self._value is not None and
            isinstance(self._value, clazz)
        )
        return self
    
    def then(self, consumer: Any) -> ConditionalOperations[T, V]:
        """Execute a consumer function or Execution if the condition was met.
        
        Args:
            consumer: Either a Callable function or an Execution object
            
        Returns:
            A ConditionalOperations instance for chaining
        """
        if self._result:
            # Check if it's an Execution object (has apply method)
            if hasattr(consumer, 'apply') and callable(getattr(consumer, 'apply', None)):
                consumer.apply()
            else:
                # It's a callable function
                consumer(self._value)
        return self
    
    def then_return(self, function: Callable[[T], V]) -> ConditionalOperations[T, V]:
        """Execute a function and return its value if the condition was met.
        
        Args:
            function: The function to execute and return its result
            
        Returns:
            A ConditionalOperations instance for chaining
        """
        if self._result:
            self._return_value = function(self._value)
        return self
    
    def or_else(self, consumer: Callable[[T], None]) -> None:
        """Execute if the condition was not met.
        
        Args:
            consumer: The function to execute if condition was not met
        """
        if not self._result:
            consumer(self._value)
    
    def value(self) -> Optional[V]:
        """Get the return value from then_return operations.
        
        Returns:
            The value returned by a then_return operation, or None
        """
        return self._return_value

