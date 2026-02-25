"""
Operations Module

This module contains operational classes for check processing.
"""

# Type alias for convenience (Callable[[], None])
from typing import Callable

from .conditional_operations import ConditionalOperations
from .execution import Execution
from .executive_operations import ExecutiveOperations
from .operations import Operations

Executable = Callable[[], None]

__all__ = [
    "Execution",
    "Executable",
    "ConditionalOperations",
    "ExecutiveOperations",
    "Operations",
]
