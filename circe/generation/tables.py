from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .config import GenerationConfig

COHORT_METADATA_SCHEMA: dict[str, str] = {
    "cohort_id": "int64",
    "cohort_name": "string",
    "target_table": "string",
    "results_schema": "string",
    "expression_hash": "string",
    "engine_version": "string",
    "generated_at": "string",
    "is_subset": "boolean",
    "parent_cohort_id": "int64",
    "subset_definition_id": "string",
    "status": "string",
}

COHORT_CHECKSUM_SCHEMA: dict[str, str] = {
    "cohort_id": "int64",
    "expression_hash": "string",
    "options_hash": "string",
    "combined_hash": "string",
    "generated_at": "string",
}

SUBSET_METADATA_SCHEMA: dict[str, str] = {
    "subset_definition_id": "string",
    "subset_name": "string",
    "parent_cohort_id": "int64",
    "operator_sequence_hash": "string",
    "generated_cohort_id": "int64",
    "dependency_hash": "string",
    "dependency_payload": "string",
    "generated_at": "string",
}

COHORT_RESULT_SCHEMA: dict[str, str] = {
    "cohort_definition_id": "int64",
    "subject_id": "int64",
    "cohort_start_date": "date",
    "cohort_end_date": "date",
}


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def table_exists(backend, table_name: str, schema: str | None = None) -> bool:
    try:
        if schema is not None:
            try:
                _ = backend.table(table_name, database=schema)
                return True
            except TypeError:
                pass
        _ = backend.table(table_name)
        return True
    except Exception:
        return False


def ensure_table(
    backend,
    *,
    table_name: str,
    schema: dict[str, str],
    database: str | None,
) -> None:
    if table_exists(backend, table_name, database):
        return

    try:
        if database is not None:
            try:
                backend.create_table(table_name, schema=schema, database=database)
                return
            except TypeError:
                pass
        backend.create_table(table_name, schema=schema)
    except Exception as exc:
        raise RuntimeError(
            f"Failed creating table '{table_name}' in schema '{database}'."
        ) from exc


def create_generation_tables(backend, config: GenerationConfig) -> None:
    ensure_table(
        backend,
        table_name=config.metadata_table,
        schema=COHORT_METADATA_SCHEMA,
        database=config.results_schema,
    )
    ensure_table(
        backend,
        table_name=config.checksum_table,
        schema=COHORT_CHECKSUM_SCHEMA,
        database=config.results_schema,
    )
    ensure_table(
        backend,
        table_name=config.subset_metadata_table,
        schema=SUBSET_METADATA_SCHEMA,
        database=config.results_schema,
    )


def table_relation(backend, table_name: str, schema: str | None):
    if schema is not None:
        try:
            return backend.table(table_name, database=schema)
        except TypeError:
            pass
    return backend.table(table_name)


def read_rows(backend, table_name: str, schema: str | None = None) -> list[dict[str, Any]]:
    if not table_exists(backend, table_name, schema):
        return []

    rows = table_relation(backend, table_name, schema).execute()
    if hasattr(rows, "to_dict"):
        return list(rows.to_dict(orient="records"))
    return []


def overwrite_rows(
    backend,
    *,
    table_name: str,
    rows: list[dict[str, Any]],
    schema: dict[str, str],
    database: str | None,
) -> None:
    try:
        if not rows:
            if database is not None:
                try:
                    backend.create_table(
                        table_name,
                        schema=schema,
                        database=database,
                        overwrite=True,
                    )
                    return
                except TypeError:
                    pass
            backend.create_table(table_name, schema=schema, overwrite=True)
            return

        import ibis

        ordered_columns = list(schema.keys())
        payload = {
            column: [row.get(column) for row in rows]
            for column in ordered_columns
        }
        memtable = ibis.memtable(payload)
        relation = memtable.select(
            *[
                memtable[column].cast(dtype).name(column)
                for column, dtype in schema.items()
            ]
        )

        if database is not None:
            try:
                backend.create_table(
                    table_name,
                    obj=relation,
                    database=database,
                    overwrite=True,
                )
                return
            except TypeError:
                pass

        backend.create_table(table_name, obj=relation, overwrite=True)
    except Exception as exc:
        raise RuntimeError(
            f"Failed writing rows to table '{table_name}' in schema '{database}'."
        ) from exc


def cohort_row_count(backend, *, config: GenerationConfig, cohort_id: int) -> int:
    if not table_exists(backend, config.cohort_table, config.results_schema):
        return 0

    relation = table_relation(backend, config.cohort_table, config.results_schema)
    if "cohort_definition_id" not in relation.columns:
        return 0
    count_expr = relation.filter(relation.cohort_definition_id == int(cohort_id)).count()
    return int(count_expr.execute())
