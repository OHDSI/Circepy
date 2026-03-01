from __future__ import annotations

import logging

from ..cohortdefinition import BuildExpressionQueryOptions, CohortExpression
from .engine.cohort import build_cohort_table
from .ibis.codesets import CachedConceptSetResolver
from .ibis.context import ExecutionContext
from .normalize.cohort import normalize_cohort
from .typing import BackendLike, Table

logger = logging.getLogger(__name__)


def build_cohort_ibis(
    expression: CohortExpression,
    *,
    backend: BackendLike,
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

    vocabulary_schema = (
        options.vocabulary_schema
        if options is not None and options.vocabulary_schema
        else cdm_schema
    )

    def _table_getter(table_name: str, schema: str | None) -> Table:
        try:
            if schema is not None:
                return backend.table(table_name, database=schema)
        except TypeError:
            pass
        return backend.table(table_name)

    resolver = CachedConceptSetResolver(
        table_getter=_table_getter,
        vocabulary_schema=vocabulary_schema,
        concept_sets=normalized.concept_sets,
    )

    ctx = ExecutionContext(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        options=options,
        concept_sets=normalized.concept_sets,
        codeset_resolver=resolver,
    )

    logger.debug("Compiling normalized plan to Ibis")
    return build_cohort_table(normalized, ctx)
