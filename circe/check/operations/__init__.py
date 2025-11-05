"""
Operations Module

This module contains operational classes for check processing.
"""

from .execution import Execution
from .conditional_operations import ConditionalOperations
from .executive_operations import ExecutiveOperations
from .operations import Operations

# Type alias for convenience (Callable[[], None])
from typing import Callable
Executable = Callable[[], None]

__all__ = [
    'Execution',
    'Executable',
    'ConditionalOperations',
    'ExecutiveOperations',
    'Operations',
]
