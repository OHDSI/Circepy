from __future__ import annotations

import sqlglot as sg
import sqlglot.expressions as sge

from ..errors import ExecutionError
from ..typing import IbisBackendLike


def _call_with_optional_database(method, *args, database: str | None, **kwargs):
    if database is not None:
        try:
            return method(*args, database=database, **kwargs)
        except TypeError:
            pass
    return method(*args, **kwargs)


def table_exists(
    backend: IbisBackendLike,
    *,
    table_name: str,
    schema: str | None,
) -> bool:
    """Return whether a backend table exists."""
    list_tables = getattr(backend, "list_tables", None)
    if callable(list_tables):
        if schema is not None:
            try:
                return table_name in list_tables(database=schema)
            except TypeError:
                return table_name in list_tables()
        return table_name in list_tables()

    try:
        read_table(backend, table_name=table_name, schema=schema)
    except Exception:
        return False
    return True


def read_table(
    backend: IbisBackendLike,
    *,
    table_name: str,
    schema: str | None,
):
    """Read a backend table as an Ibis relation."""
    return _call_with_optional_database(
        backend.table,
        table_name,
        database=schema,
    )


def create_table(
    backend: IbisBackendLike,
    *,
    table_name: str,
    schema: str | None,
    **kwargs,
) -> None:
    """Create or overwrite a backend table with schema fallback."""
    _call_with_optional_database(
        backend.create_table,
        table_name,
        database=schema,
        **kwargs,
    )


def cohort_rows_exist(
    backend: IbisBackendLike,
    *,
    cohort_table: str,
    results_schema: str | None,
    cohort_id: int,
) -> bool:
    """Return whether a cohort table already contains rows for a cohort id."""
    import ibis

    try:
        table = read_table(backend, table_name=cohort_table, schema=results_schema)
        cohort_id_expr = ibis.literal(int(cohort_id), type="int64")
        matching = table.filter(table.cohort_definition_id.cast("int64") == cohort_id_expr)
        return len(matching.limit(1).execute()) > 0
    except Exception as exc:
        raise ExecutionError(
            f"Ibis executor write error: failed checking existing rows for cohort_id={cohort_id}."
        ) from exc


def delete_cohort_rows(
    backend: IbisBackendLike,
    *,
    cohort_table: str,
    results_schema: str | None,
    cohort_id: int,
) -> None:
    """Delete existing cohort-table rows for a single cohort id."""
    raw_sql = getattr(backend, "raw_sql", None)
    if not callable(raw_sql):
        raise ExecutionError(
            "Ibis executor write error: backend does not support raw_sql for cohort-table deletes."
        )

    catalog, database = _catalog_db_tuple(backend, results_schema)
    quoted = getattr(getattr(backend, "compiler", None), "quoted", False)
    statement = sge.delete(sg.table(cohort_table, db=database, catalog=catalog, quoted=quoted)).where(
        sg.column("cohort_definition_id", quoted=quoted).eq(sge.convert(int(cohort_id)))
    )

    try:
        raw_sql(statement)
    except Exception as exc:
        raise ExecutionError(
            "Ibis executor write error: failed deleting existing cohort rows from "
            f"'{cohort_table}' for cohort_id={cohort_id}."
        ) from exc


def supports_transactional_replace(backend: IbisBackendLike) -> bool:
    """Return whether cohort-scoped delete+insert can run transactionally."""
    return getattr(backend, "name", None) in {"duckdb", "postgres"}


def replace_cohort_rows_transactionally(
    relation,
    *,
    backend: IbisBackendLike,
    cohort_table: str,
    results_schema: str | None,
    cohort_id: int,
) -> None:
    """Replace one cohort's rows atomically using delete+insert when supported."""
    if not supports_transactional_replace(backend):
        raise ExecutionError(
            "Ibis executor write error: backend does not support transactional cohort-table replace."
        )

    _run_transaction_control(backend, "BEGIN")
    try:
        delete_cohort_rows(
            backend,
            cohort_table=cohort_table,
            results_schema=results_schema,
            cohort_id=cohort_id,
        )
        insert_relation(
            relation,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
        )
    except Exception:
        _run_transaction_control(backend, "ROLLBACK")
        raise
    else:
        _run_transaction_control(backend, "COMMIT")


def exclude_cohort_rows(table, *, cohort_id: int):
    """Filter an existing cohort table to all cohort ids except one."""
    import ibis

    cohort_id_expr = ibis.literal(int(cohort_id), type="int64")
    try:
        return table.filter(table.cohort_definition_id.cast("int64") != cohort_id_expr)
    except Exception as exc:
        raise ExecutionError(
            f"Ibis executor write error: failed removing existing rows for cohort_id={cohort_id}."
        ) from exc


def insert_relation(
    relation,
    *,
    backend: IbisBackendLike,
    target_table: str,
    target_schema: str | None,
) -> None:
    """Insert an Ibis relation into an existing backend table."""
    insert = getattr(backend, "insert", None)
    if not callable(insert):
        raise ExecutionError(
            "Ibis executor write error: backend does not support insert for cohort-table writes."
    )

    try:
        _call_with_optional_database(
            insert,
            target_table,
            relation,
            database=target_schema,
            overwrite=False,
        )
    except Exception as exc:
        schema_label = target_schema if target_schema is not None else "<default>"
        raise ExecutionError(
            "Ibis executor write error: failed inserting relation into "
            f"table '{target_table}' in schema '{schema_label}'."
        ) from exc


def _run_transaction_control(backend: IbisBackendLike, statement: str) -> None:
    raw_sql = getattr(backend, "raw_sql", None)
    if not callable(raw_sql):
        raise ExecutionError(
            "Ibis executor write error: backend does not support raw_sql for transactional cohort writes."
        )

    try:
        raw_sql(statement)
    except Exception as exc:
        raise ExecutionError(
            f"Ibis executor write error: failed executing transaction statement {statement!r}."
        ) from exc


def _catalog_db_tuple(backend: IbisBackendLike, schema: str | None) -> tuple[str | None, str | None]:
    if schema is None:
        return None, None

    to_sqlglot_table = getattr(backend, "_to_sqlglot_table", None)
    to_catalog_db_tuple = getattr(backend, "_to_catalog_db_tuple", None)
    if callable(to_sqlglot_table) and callable(to_catalog_db_tuple):
        try:
            return to_catalog_db_tuple(to_sqlglot_table(schema))
        except Exception:
            pass

    return None, schema
