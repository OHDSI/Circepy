from __future__ import annotations


class ExecutionError(RuntimeError):
    """Base execution subsystem error."""


class ExecutionNormalizationError(ExecutionError):
    """Raised when expression normalization fails structurally."""


class UnsupportedCriterionError(ExecutionError):
    """Raised when a criterion type is unsupported by the executor."""


class UnsupportedFeatureError(ExecutionError):
    """Raised when requested executor semantics are unsupported."""


class CompilationError(ExecutionError):
    """Raised when lowering/compilation to Ibis cannot proceed."""
