from __future__ import annotations

import logging

from ..cohortdefinition import BuildExpressionQueryOptions, CohortExpression
from .engine.cohort import build_cohort_table
from .ibis.context import make_execution_context
from .normalize.cohort import normalize_cohort
from .typing import IbisBackendLike, Table

logger = logging.getLogger(__name__)


def build_cohort_ibis(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: str | None = None,
    options: BuildExpressionQueryOptions | None = None,
) -> Table:
    """Build a cohort as an Ibis table using the new execution subsystem.

    This path coexists with the existing SQL-builder API and keeps the
    `circe.cohortdefinition` public model layer unchanged.

    Note:
        The Ibis executor is experimental and feature-complete for currently
        implemented semantics. `custom_era` remains unsupported.
    """

    logger.debug("Normalizing CohortExpression for Ibis execution")
    normalized = normalize_cohort(expression, options)

    ctx = make_execution_context(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        options=options,
        concept_sets=normalized.concept_sets,
    )

    logger.debug("Compiling normalized plan to Ibis")
    return build_cohort_table(normalized, ctx)
