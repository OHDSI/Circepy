from __future__ import annotations

from typing import Literal

from ..cohortdefinition import CohortExpression
from .databricks_compat import maybe_apply_databricks_post_connect_workaround
from .engine.cohort import build_cohort_table
from .errors import ExecutionError
from .ibis.codesets import build_single_codeset_table
from .ibis.context import make_execution_context
from .ibis.materialize import project_to_ohdsi_cohort_table
from .ibis.operations import (
    cohort_rows_exist,
    create_table,
    exclude_cohort_rows,
    insert_relation,
    read_table,
    replace_cohort_rows_transactionally,
    supports_transactional_replace,
    table_exists,
)
from .normalize.cohort import normalize_cohort
from .typing import IbisBackendLike, Table


def build_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    use_persistent_cache: bool = False,
    cohort_id: int = 0,
    materialize: bool = True,
    codeset_table: Table | None = None,
) -> Table:
    """Normalize, compile, and assemble a cohort relation.

    Paths through stage-by-stage temp tables when *cohort_id* is provided
    and *materialize* is True, so that the ibis expression tree never grows
    too large to compile.  Set *materialize=False* for compile-only use
    (e.g. unit tests that only verify the expression tree can be built).

    When *codeset_table* is provided (from a batch-generation caller), it is
    used directly.  Otherwise one is auto-created for this single cohort and
    dropped after the pipeline runs.
    """
    maybe_apply_databricks_post_connect_workaround(backend)

    normalized = normalize_cohort(expression)

    if codeset_table is not None:
        own_table = False
    else:
        codeset_table = build_single_codeset_table(
            backend=backend,
            concept_sets=normalized.concept_sets,
            batch_table_name=f"__cg_{cohort_id}_codesets",
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
        )
        own_table = True

    ctx = make_execution_context(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        codeset_table=codeset_table,
    )
    return build_cohort_table(normalized, ctx, cohort_id=cohort_id, materialize=materialize)


def write_relation(
    relation: Table,
    *,
    backend: IbisBackendLike,
    target_table: str,
    target_schema: str | None = None,
    if_exists: Literal["fail", "replace"] = "fail",
    temporary: bool = False,
) -> None:
    """Materialize a relation to a backend table."""
    if if_exists not in {"fail", "replace"}:
        raise ValueError("if_exists must be one of {'fail', 'replace'} for write_relation.")

    maybe_apply_databricks_post_connect_workaround(backend)

    write_kwargs = {
        "obj": relation,
        "overwrite": if_exists == "replace",
    }
    if temporary:
        write_kwargs["temp"] = True

    try:
        create_table(
            backend,
            table_name=target_table,
            schema=target_schema,
            **write_kwargs,
        )
    except Exception as exc:
        schema_label = target_schema if target_schema is not None else "<default>"
        raise ExecutionError(
            "Ibis executor write error: failed writing relation to "
            f"table '{target_table}' in schema '{schema_label}' "
            f"(if_exists={if_exists!r}, temporary={temporary})."
        ) from exc


def write_cohort(
    expression: CohortExpression | None = None,
    *,
    compiled_relation: Table | None = None,
    backend: IbisBackendLike,
    cdm_schema: str,
    cohort_table: str,
    cohort_id: int,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    if_exists: Literal["fail", "replace"] = "fail",
    use_persistent_cache: bool = False,
) -> None:
    """Build cohort rows and materialize them with cohort-scoped semantics.

    Args:
        expression: Cohort expression to compile and execute. Provide one of
            ``expression`` or ``compiled_relation`` (not both).
        compiled_relation: A pre-compiled ibis relation (output of
            ``build_cohort()`` projected with ``project_to_ohdsi_cohort_table()``).
            When provided, the compilation step is skipped and this relation is
            materialized directly. Use this to isolate database-execution time
            from query-compilation time in benchmarks.
        backend: Ibis backend connection.
        cdm_schema: Schema containing the OMOP CDM source tables.
        cohort_table: Name of the OHDSI cohort table to write results into.
        cohort_id: The cohort_definition_id value to stamp on written rows.
        results_schema: Schema for the cohort table.
        vocabulary_schema: Schema for vocabulary tables (defaults to cdm_schema).
        if_exists: Behaviour when cohort rows already exist.  One of
            ``"fail"`` (raise) or ``"replace"`` (remove existing rows for
            this cohort_id before writing).
        use_persistent_cache: Whether to cache concept set lookups persistently.

    Raises:
        ValueError: If both or neither of ``expression`` / ``compiled_relation``
            are provided, or ``if_exists`` is invalid.
        ExecutionError: If the write fails.
    """
    if (expression is None) == (compiled_relation is None):
        raise ValueError("Exactly one of expression or compiled_relation must be provided.")
    if if_exists not in {"fail", "replace"}:
        raise ValueError("if_exists must be one of {'fail', 'replace'} for write_cohort.")

    if compiled_relation is not None:
        new_rows = compiled_relation
    else:
        new_rows = build_cohort(
            expression,  # type: ignore[arg-type]
            backend=backend,
            cdm_schema=cdm_schema,
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
            use_persistent_cache=use_persistent_cache,
            cohort_id=cohort_id,
        )
        new_rows = project_to_ohdsi_cohort_table(new_rows, cohort_id=cohort_id)

    if not table_exists(backend, table_name=cohort_table, schema=results_schema):
        write_relation(
            new_rows,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
            if_exists="fail",
        )
        return

    if if_exists == "fail":
        if cohort_rows_exist(
            backend,
            cohort_table=cohort_table,
            results_schema=results_schema,
            cohort_id=cohort_id,
        ):
            raise ExecutionError(
                "Ibis executor write error: cohort table "
                f"'{cohort_table}' already contains rows for cohort_id={cohort_id}."
            )
        insert_relation(
            new_rows,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
        )
        return

    if supports_transactional_replace(backend):
        replace_cohort_rows_transactionally(
            new_rows,
            backend=backend,
            cohort_table=cohort_table,
            results_schema=results_schema,
            cohort_id=cohort_id,
        )
        return

    existing = read_table(
        backend,
        table_name=cohort_table,
        schema=results_schema,
    )
    filtered = exclude_cohort_rows(existing, cohort_id=cohort_id)
    relation = filtered.union(new_rows, distinct=False)
    write_relation(
        relation,
        backend=backend,
        target_table=cohort_table,
        target_schema=results_schema,
        if_exists="replace",
    )
