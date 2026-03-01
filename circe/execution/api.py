from __future__ import annotations

import logging
from typing import Literal

from ..cohortdefinition import BuildExpressionQueryOptions, CohortExpression
from .engine.cohort import build_cohort_table
from .errors import ExecutionError
from .ibis.context import make_execution_context
from .normalize.cohort import normalize_cohort
from .typing import IbisBackendLike, Table

logger = logging.getLogger(__name__)


def build_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: str | None = None,
    options: BuildExpressionQueryOptions | None = None,
) -> Table:
    """Build a cohort as a relational table expression.

    This path coexists with the SQL-string API and keeps the
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


def write_relation(
    relation: Table,
    *,
    backend: IbisBackendLike,
    target_table: str,
    results_schema: str | None = None,
    if_exists: Literal["fail", "replace"] = "fail",
    temporary: bool = False,
) -> None:
    """Write a relation to a backend table.

    This is an internal helper used by `write_cohort`.
    """
    if if_exists not in {"fail", "replace"}:
        raise ValueError(
            "if_exists must be one of {'fail', 'replace'} for write_relation."
        )

    write_kwargs = {
        "obj": relation,
        "overwrite": if_exists == "replace",
    }
    if temporary:
        write_kwargs["temp"] = True

    try:
        if results_schema is not None:
            try:
                backend.create_table(
                    target_table,
                    database=results_schema,
                    **write_kwargs,
                )
                return
            except TypeError:
                # Some backends do not support explicit database/schema routing.
                pass

        backend.create_table(target_table, **write_kwargs)
    except TypeError as exc:
        if temporary:
            raise ExecutionError(
                "Ibis executor write error: backend does not support temporary "
                "table creation via create_table(..., temp=True)."
            ) from exc
        raise ExecutionError(
            "Ibis executor write error: backend does not support the required "
            "create_table signature."
        ) from exc
    except Exception as exc:
        schema_label = results_schema if results_schema is not None else "<default>"
        raise ExecutionError(
            "Ibis executor write error: failed writing relation to "
            f"table '{target_table}' in schema '{schema_label}' "
            f"(if_exists={if_exists!r}, temporary={temporary})."
        ) from exc


def write_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    target_table: str,
    results_schema: str | None = None,
    options: BuildExpressionQueryOptions | None = None,
    if_exists: Literal["fail", "replace"] = "fail",
    temporary: bool = False,
) -> None:
    """Build and materialize a cohort relation to a database table."""
    relation = build_cohort(
        expression,
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        options=options,
    )
    write_relation(
        relation,
        backend=backend,
        target_table=target_table,
        results_schema=(results_schema or cdm_schema),
        if_exists=if_exists,
        temporary=temporary,
    )


# Compatibility aliases for transition period.
build_cohort_ibis = build_cohort
write_cohort_ibis = write_cohort
