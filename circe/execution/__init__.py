"""New Ibis execution subsystem.

This package is intentionally parallel to the existing SQL builder path and does
not modify cohortdefinition model semantics.
"""

from .api import (
    build_cohort,
    calculate_cohort_metrics,
    evaluate_cohort,
    write_cohort,
    write_evaluation,
    write_relation,
)
from .databricks_compat import apply_databricks_post_connect_workaround
from .engine.cohort import build_cohort_table
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
    "evaluate_cohort",
    "write_evaluation",
    "calculate_cohort_metrics",
    "write_relation",
    "apply_databricks_post_connect_workaround",
    "ExecutionError",
    "ExecutionNormalizationError",
    "UnsupportedCriterionError",
    "UnsupportedFeatureError",
    "CompilationError",
    "build_cohort_table",
]
