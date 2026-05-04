"""Persistent checksum storage for incremental cohort generation.

The checksum table records the SHA-256 hash of each successfully generated
cohort's expression. On subsequent incremental runs, cohorts whose expression
hash matches the stored value are skipped.

Table schema (cohort_checksum):
    cohort_definition_id  int64
    checksum              str
    generation_end_time   timestamp
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ..execution.ibis.operations import create_table, read_table, table_exists

if TYPE_CHECKING:
    from ..execution.typing import IbisBackendLike


def load_checksums(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    table_name: str,
) -> dict[int, str]:
    """Load stored checksums from the checksum table.

    Returns a mapping of cohort_id -> checksum for the most recently recorded
    completed generation of each cohort.  Returns an empty dict if the table
    does not yet exist.

    Args:
        backend: Ibis backend connection.
        schema: Schema/database where the checksum table lives.
        table_name: Name of the checksum table.

    Returns:
        dict mapping cohort_id (int) -> checksum (str).
    """
    if not table_exists(backend, table_name=table_name, schema=schema):
        return {}

    table = read_table(backend, table_name=table_name, schema=schema)
    rows = table.execute()
    # In case there are multiple rows per cohort (shouldn't happen but be safe),
    # keep the most recent by generation_end_time.
    if rows.empty:
        return {}

    if "generation_end_time" in rows.columns:
        rows = rows.sort_values("generation_end_time", ascending=False)
        rows = rows.drop_duplicates(subset=["cohort_definition_id"], keep="first")

    return {int(row["cohort_definition_id"]): str(row["checksum"]) for _, row in rows.iterrows()}


def save_checksums(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    table_name: str,
    completed: dict[int, tuple[str, datetime]],
) -> None:
    """Persist checksums for successfully generated cohorts.

    Uses the same read-filter-union-rewrite pattern as ``write_cohort`` so it
    works on every ibis backend without requiring raw SQL.

    Args:
        backend: Ibis backend connection.
        schema: Schema/database where the checksum table should be written.
        table_name: Name of the checksum table.
        completed: Mapping of cohort_id -> (checksum, generation_end_time) for
            cohorts that completed successfully in this run.
    """
    if not completed:
        return

    import ibis
    import pandas as pd

    new_rows_df = pd.DataFrame(
        [
            {
                "cohort_definition_id": cohort_id,
                "checksum": checksum,
                "generation_end_time": end_time,
            }
            for cohort_id, (checksum, end_time) in completed.items()
        ]
    )
    new_rows_df["cohort_definition_id"] = new_rows_df["cohort_definition_id"].astype("int64")
    new_rows_df["checksum"] = new_rows_df["checksum"].astype(str)
    new_rows_df["generation_end_time"] = pd.to_datetime(new_rows_df["generation_end_time"])

    new_relation = ibis.memtable(new_rows_df)

    if not table_exists(backend, table_name=table_name, schema=schema):
        create_table(backend, table_name=table_name, schema=schema, obj=new_relation, overwrite=False)
        return

    # Merge: keep existing rows for cohorts NOT in this batch, union new rows.
    existing = read_table(backend, table_name=table_name, schema=schema)
    updated_ids = list(completed.keys())
    filtered_existing = existing.filter(
        ~existing.cohort_definition_id.cast("int64").isin(
            [ibis.literal(int(i), type="int64") for i in updated_ids]
        )
    )
    # Cast new rows to match the existing table's timestamp type to avoid union schema conflicts.
    ts_type = existing.schema()["generation_end_time"]
    new_relation = new_relation.mutate(generation_end_time=new_relation.generation_end_time.cast(ts_type))
    merged = filtered_existing.union(new_relation, distinct=False)
    create_table(backend, table_name=table_name, schema=schema, obj=merged, overwrite=True)
