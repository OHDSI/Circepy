"""New Ibis execution subsystem.

This package is intentionally parallel to the existing SQL builder path and does
not modify cohortdefinition model semantics.
"""

from .databricks_compat import apply_databricks_post_connect_workaround
from .api import build_cohort, build_cohort_ibis, write_cohort, write_cohort_ibis
from .errors import (
    CompilationError,
    ExecutionError,
    ExecutionNormalizationError,
    UnsupportedCriterionError,
    UnsupportedFeatureError,
)

apply_databricks_post_connect_workaround()

__all__ = [
    "build_cohort",
    "write_cohort",
    "build_cohort_ibis",
    "write_cohort_ibis",
    "apply_databricks_post_connect_workaround",
    "ExecutionError",
    "ExecutionNormalizationError",
    "UnsupportedCriterionError",
    "UnsupportedFeatureError",
    "CompilationError",
]
