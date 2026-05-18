"""New Ibis execution subsystem.

This package is intentionally parallel to the existing SQL builder path and does
not modify cohortdefinition model semantics.
"""

from .api import build_cohort, write_cohort
from .databricks_compat import apply_databricks_post_connect_workaround
from .errors import (
    CompilationError,
    ExecutionError,
    ExecutionNormalizationError,
    UnsupportedCriterionError,
    UnsupportedFeatureError,
)
from .ibis.codesets import resolve_concept_sets

__all__ = [
    "build_cohort",
    "write_cohort",
    "resolve_concept_sets",
    "apply_databricks_post_connect_workaround",
    "ExecutionError",
    "ExecutionNormalizationError",
    "UnsupportedCriterionError",
    "UnsupportedFeatureError",
    "CompilationError",
]
