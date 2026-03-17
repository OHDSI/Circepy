"""New Ibis execution subsystem.

This package is intentionally parallel to the existing SQL builder path and does
not modify cohortdefinition model semantics.
"""

from .api import build_cohort, build_cohort_ibis, write_cohort, write_cohort_ibis
from .compat import ExecutionOptions, IbisExecutor, build_ibis, to_polars
from .databricks_compat import apply_databricks_post_connect_workaround
from .errors import (
    CompilationError,
    ExecutionError,
    ExecutionNormalizationError,
    UnsupportedCriterionError,
    UnsupportedFeatureError,
)

__all__ = [
    "build_cohort",
    "write_cohort",
    "build_cohort_ibis",
    "write_cohort_ibis",
    "ExecutionOptions",
    "IbisExecutor",
    "build_ibis",
    "to_polars",
    "apply_databricks_post_connect_workaround",
    "ExecutionError",
    "ExecutionNormalizationError",
    "UnsupportedCriterionError",
    "UnsupportedFeatureError",
    "CompilationError",
]
