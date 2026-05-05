from __future__ import annotations

from typing import Literal

from ..cohortdefinition import CohortExpression
from .databricks_compat import maybe_apply_databricks_post_connect_workaround
from .engine.cohort import build_cohort_table
from .errors import ExecutionError
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
) -> Table:
    """Normalize, compile, and assemble a cohort relation."""
    maybe_apply_databricks_post_connect_workaround(backend)

    normalized = normalize_cohort(expression)

    ctx = make_execution_context(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        concept_sets=normalized.concept_sets,
        use_persistent_cache=use_persistent_cache,
    )

    return build_cohort_table(normalized, ctx)


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


def build_cohort_relation(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    cohort_id: int,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
) -> Table:
    """Build cohort relation and project to OHDSI format without materializing.

    This returns a lazy Ibis expression ready to be written to a table.
    Useful for benchmarking or when you want to separate compilation from execution.
    """
    cohort_expr = build_cohort(
        expression,
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
    )
    return project_to_ohdsi_cohort_table(cohort_expr, cohort_id=cohort_id)


def write_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    cohort_table: str,
    cohort_id: int,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    if_exists: Literal["fail", "replace"] = "fail",
    use_persistent_cache: bool = False,
) -> None:
    """Build cohort rows and materialize them with cohort-scoped semantics."""
    if if_exists not in {"fail", "replace"}:
        raise ValueError("if_exists must be one of {'fail', 'replace'} for write_cohort.")

    new_rows = build_cohort_relation(
        expression,
        backend=backend,
        cdm_schema=cdm_schema,
        cohort_id=cohort_id,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        use_persistent_cache=use_persistent_cache,
    )

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


def write_cohort_relation(
    cohort_relation: Table,
    *,
    backend: IbisBackendLike,
    cohort_table: str,
    cohort_id: int,
    results_schema: str | None = None,
    if_exists: Literal["fail", "replace", "append"] = "fail",
    skip_validation: bool = False,
) -> None:
    """Write a pre-built cohort relation to a table.

    This function takes a cohort relation (from build_cohort_relation) and writes it
    to the target table. Useful for benchmarking when you want to separate compilation
    from execution.

    Args:
        cohort_relation: Pre-built cohort relation (from build_cohort_relation)
        backend: Ibis backend connection
        cohort_table: Name of the target cohort table
        cohort_id: Cohort definition ID (for checking conflicts)
        results_schema: Schema containing the cohort table
        if_exists: What to do if cohort rows exist: "fail", "replace", or "append"
        skip_validation: Skip table existence and cohort row checks (faster, use for benchmarking)
    """
    if if_exists not in {"fail", "replace", "append"}:
        raise ValueError("if_exists must be one of {'fail', 'replace', 'append'} for write_cohort_relation.")

    # Fast path for benchmarking: skip all validation checks
    if skip_validation:
        insert_relation(
            cohort_relation,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
        )
        return

    if not table_exists(backend, table_name=cohort_table, schema=results_schema):
        write_relation(
            cohort_relation,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
            if_exists="fail",
        )
        return

    if if_exists == "append":
        # Just append without checking for existing rows
        insert_relation(
            cohort_relation,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
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
            cohort_relation,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
        )
        return

    # if_exists == "replace"
    if supports_transactional_replace(backend):
        replace_cohort_rows_transactionally(
            cohort_relation,
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
    relation = filtered.union(cohort_relation, distinct=False)
    write_relation(
        relation,
        backend=backend,
        target_table=cohort_table,
        target_schema=results_schema,
        if_exists="replace",
    )
