from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from ..cohortdefinition import BuildExpressionQueryOptions, CohortExpression
from .engine.cohort import build_cohort_table
from .ibis.context import ExecutionContext
from .normalize.cohort import normalize_cohort

if TYPE_CHECKING:
    import ibis

logger = logging.getLogger(__name__)


def build_cohort_ibis(
    expression: CohortExpression,
    *,
    backend: Any,
    cdm_schema: str,
    results_schema: str | None = None,
    options: Optional[BuildExpressionQueryOptions] = None,
) -> Any:
    """Build a cohort as an Ibis table using the new execution subsystem.

    This path coexists with the existing SQL-builder API and keeps the
    `circe.cohortdefinition` public model layer unchanged.
    """

    logger.debug("Normalizing CohortExpression for Ibis execution")
    normalized = normalize_cohort(expression, options)

    ctx = ExecutionContext(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        options=options,
        concept_sets=normalized.concept_sets,
    )

    logger.debug("Compiling normalized plan to Ibis")
    return build_cohort_table(normalized, ctx)
