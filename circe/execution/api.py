from __future__ import annotations

import contextlib
import uuid
from typing import Literal

import sqlglot as sg
from ibis.backends.sql.compilers.base import AlterTable, RenameTable

from ..cohortdefinition import CohortExpression
from .databricks_compat import maybe_apply_databricks_post_connect_workaround
from .engine.cohort import _drop_staging_tables, build_cohort_table
from .errors import ExecutionError
from .ibis.codesets import build_single_codeset_table
from .ibis.context import make_execution_context
from .ibis.materialize import project_to_ohdsi_cohort_table
from .ibis.operations import (
    _catalog_db_tuple,
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
from .session import register_session, report_stale_sessions, unregister_session
from .typing import IbisBackendLike, Table


def build_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    cohort_id: int = 0,
    materialize: bool = True,
    codeset_table: Table | None = None,
    cohort_table: str = "cohort",
    session_prefix: str = "",
) -> Table:
    """Normalize, compile, and assemble a cohort relation.

    Paths through stage-by-stage temp tables when *cohort_id* is provided
    and *materialize* is True, so that the ibis expression tree never grows
    too large to compile.  Set *materialize=False* for compile-only use.

    When *codeset_table* is provided it is used directly.  Otherwise a
    per-cohort codeset table is auto-created.
    """
    maybe_apply_databricks_post_connect_workaround(backend)

    # Bound the correlated-criteria cache to this build.  The cache is keyed by
    # execution context, so entries from a previous build are never re-hit;
    # clearing here prevents the module-global dict from pinning prior backends
    # and codeset tables for the lifetime of the process.
    from .engine.group_operators import _COMPILED_CORRELATED_EVENTS

    _COMPILED_CORRELATED_EVENTS.clear()

    normalized = normalize_cohort(expression)

    # Resolve the vocabulary schema once at the API boundary so that concept
    # expansion (descendants / mapped concepts) reads from the same schema the
    # execution context uses.  Without this, the vocabulary lookup defaults to
    # the backend's default schema instead of ``cdm_schema`` (#45).
    vocabulary_schema = vocabulary_schema or cdm_schema

    # The codeset table, staging tables, and session registry all live in the
    # same schema so that cleanup and stale-table detection agree (#57).
    session_schema = results_schema or cdm_schema

    # Default to a unique session prefix so that building a second cohort on the
    # same backend/schema does not overwrite the ``__codesets`` / staging tables
    # that an earlier, still-live relation depends on (#50).
    if not session_prefix:
        session_prefix = f"__c_{uuid.uuid4().hex[:8]}_"
        # Direct build: surface any orphaned staging tables from prior (possibly
        # crashed) runs, and register this build's session.
        report_stale_sessions(backend, schema=session_schema)
        register_session(backend, schema=session_schema, session_prefix=session_prefix)

    if codeset_table is None:
        codeset_table = build_single_codeset_table(
            backend=backend,
            concept_sets=normalized.concept_sets,
            batch_table_name="__codesets",
            results_schema=session_schema,
            vocabulary_schema=vocabulary_schema,
            session_prefix=session_prefix,
        )

    ctx = make_execution_context(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        codeset_table=codeset_table,
    )

    return build_cohort_table(
        normalized,
        ctx,
        cohort_id=cohort_id,
        materialize=materialize,
        cohort_table=cohort_table,
        session_prefix=session_prefix,
    )


def _is_databricks_backend(backend: IbisBackendLike) -> bool:
    return getattr(backend, "name", None) == "databricks"


def _rename_table(
    backend: IbisBackendLike,
    old_name: str,
    new_name: str,
    schema: str | None,
) -> None:
    """Rename a table with a fully qualified Databricks ALTER TABLE statement."""
    catalog, database = _catalog_db_tuple(backend, schema)
    quoted = getattr(getattr(backend, "compiler", None), "quoted", False)
    old = sg.table(old_name, catalog=catalog, db=database, quoted=quoted)
    new = sg.table(new_name, catalog=catalog, db=database, quoted=quoted)
    statement = AlterTable(
        this=old,
        exists=False,
        actions=[RenameTable(this=new, exists=True)],
    )
    backend.raw_sql(statement.sql(dialect=getattr(backend, "name", "databricks")))


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
    if target_table is None or not str(target_table).strip():
        raise ExecutionError(
            "Ibis executor write error: target cohort table name is empty. "
            "Pass a non-empty cohort_table / target_table value."
        )

    maybe_apply_databricks_post_connect_workaround(backend)

    write_kwargs = {
        "obj": relation,
        "overwrite": if_exists == "replace",
    }
    if temporary:
        write_kwargs["temp"] = True

    try:
        if if_exists == "replace" and not temporary and _is_databricks_backend(backend):
            # Databricks' ibis create_table(overwrite=True) issues its own DROP
            # TABLE using an internally built identifier. On some ibis 12
            # workspaces that renders as bare "DROP TABLE IF EXISTS". Stage the
            # new relation first (it may read the existing table), then replace
            # the target with a validated rename.
            staged_table = f"{target_table}__circe_new_{uuid.uuid4().hex[:8]}"
            create_table(
                backend,
                table_name=staged_table,
                schema=target_schema,
                obj=relation,
                overwrite=False,
            )
            try:
                if table_exists(backend, table_name=target_table, schema=target_schema):
                    backend.drop_table(str(target_table), database=target_schema, force=True)
                _rename_table(backend, staged_table, target_table, target_schema)
            except Exception:
                with contextlib.suppress(Exception):
                    backend.drop_table(staged_table, database=target_schema, force=True)
                raise
        else:
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

    session_prefix = ""
    cleanup_schema = results_schema or cdm_schema

    if compiled_relation is not None:
        new_rows = compiled_relation
    else:
        session_prefix = f"__w_{uuid.uuid4().hex[:8]}_"
        report_stale_sessions(backend, schema=cleanup_schema)
        register_session(backend, schema=cleanup_schema, session_prefix=session_prefix)
        new_rows = build_cohort(
            expression,  # type: ignore[arg-type]
            backend=backend,
            cdm_schema=cdm_schema,
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
            cohort_id=cohort_id,
            session_prefix=session_prefix,
        )
        new_rows = project_to_ohdsi_cohort_table(new_rows, cohort_id=cohort_id)

    try:
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
    finally:
        if session_prefix:
            _drop_staging_tables(backend, cleanup_schema, session_prefix)
            unregister_session(backend, schema=cleanup_schema, session_prefix=session_prefix)
