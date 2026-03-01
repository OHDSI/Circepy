from __future__ import annotations

from typing import Any

import ibis

from ..execution.typing import IbisBackendLike, Table
from .config import GenerationConfig, GenerationPolicy
from .tables import COHORT_RESULT_SCHEMA, read_rows, table_exists, table_relation


def project_to_cohort_relation(relation: Table, *, cohort_id: int) -> Table:
    return relation.select(
        ibis.literal(int(cohort_id), type="int64").name("cohort_definition_id"),
        relation.person_id.cast("int64").name("subject_id"),
        relation.start_date.cast("date").name("cohort_start_date"),
        relation.end_date.cast("date").name("cohort_end_date"),
    )


def upsert_single_row(
    backend: IbisBackendLike,
    *,
    table_name: str,
    schema: dict[str, str],
    database: str | None,
    key_field: str,
    row: dict[str, Any],
) -> None:
    from .tables import overwrite_rows

    rows = read_rows(backend, table_name, database)
    filtered = [r for r in rows if str(r.get(key_field)) != str(row.get(key_field))]
    filtered.append(row)
    overwrite_rows(
        backend,
        table_name=table_name,
        rows=filtered,
        schema=schema,
        database=database,
    )


def target_rows_relation(
    backend: IbisBackendLike,
    *,
    config: GenerationConfig,
    cohort_id: int,
    new_rows: Table,
) -> Table:
    normalized_new = new_rows.select(
        *[
            new_rows[column].cast(dtype).name(column)
            for column, dtype in COHORT_RESULT_SCHEMA.items()
        ]
    )

    if table_exists(backend, config.cohort_table, config.results_schema):
        existing = table_relation(backend, config.cohort_table, config.results_schema)
        if "cohort_definition_id" in existing.columns:
            keep = existing.filter(existing.cohort_definition_id != int(cohort_id))
            normalized_keep = keep.select(
                *[
                    keep[column].cast(dtype).name(column)
                    for column, dtype in COHORT_RESULT_SCHEMA.items()
                ]
            )
            return normalized_keep.union(normalized_new, distinct=False)
    return normalized_new


def effective_policy(
    config: GenerationConfig,
    policy: GenerationPolicy | None,
) -> GenerationPolicy:
    return config.default_policy if policy is None else policy
