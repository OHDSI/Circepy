"""Persistent generation history for incremental cohort generation.

The generation history table records the SHA-256 checksum of each generated
cohort's expression alongside its generation status, start time, and end time.
On subsequent incremental runs, cohorts whose expression checksum matches the
most recent stored value are skipped.

This table serves as the canonical source of truth for per-cohort generation
timing, enabling fair benchmarks across implementations.

Table schema (v2, introduced 0.3.0):
    cohort_definition_id  int64
    checksum              str
    status                str          -- "COMPLETE" or "FAILED"
    start_time            timestamp
    end_time              timestamp

The original v1 schema stored only ``(cohort_definition_id, checksum,
generation_end_time)`` and is still handled transparently for reads.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ..execution.ibis.operations import create_table, read_table, table_exists

if TYPE_CHECKING:
    import pandas as pd

    from ..execution.typing import IbisBackendLike


def load_checksums(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    table_name: str,
) -> dict[int, str]:
    """Load stored checksums from the generation history table.

    Returns a mapping of cohort_id -> checksum for the most recently recorded
    completed generation of each cohort.  Returns an empty dict if the table
    does not yet exist.

    Args:
        backend: Ibis backend connection.
        schema: Schema/database where the table lives.
        table_name: Name of the table (may be v1 ``cohort_checksum`` or v2
            ``cohort_generation_history`` format).

    Returns:
        dict mapping cohort_id (int) -> checksum (str).
    """
    if not table_exists(backend, table_name=table_name, schema=schema):
        return {}

    table = read_table(backend, table_name=table_name, schema=schema)
    rows = table.execute()
    if rows.empty:
        return {}

    time_col = "end_time" if "end_time" in rows.columns else "generation_end_time"
    has_status = "status" in rows.columns

    if has_status:
        rows = rows[rows["status"] == "COMPLETE"]
        if rows.empty:
            return {}

    if time_col in rows.columns:
        rows = rows.sort_values(time_col, ascending=False)
        rows = rows.drop_duplicates(subset=["cohort_definition_id"], keep="first")

    return {int(row["cohort_definition_id"]): str(row["checksum"]) for _, row in rows.iterrows()}


def load_generation_history(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    table_name: str,
) -> pd.DataFrame | None:
    """Load the full generation history from the history table.

    Returns all columns (cohort_definition_id, checksum, status, start_time,
    end_time) for every recorded generation.  Returns ``None`` if the table
    does not exist or was created with the v1 schema that lacks timing
    columns.

    Args:
        backend: Ibis backend connection.
        schema: Schema/database where the table lives.
        table_name: Name of the generation history table.

    Returns:
        DataFrame with per-cohort history, or ``None`` if unavailable.
    """
    if not table_exists(backend, table_name=table_name, schema=schema):
        return None

    table = read_table(backend, table_name=table_name, schema=schema)
    rows = table.execute()
    if rows.empty:
        return None

    if "start_time" not in rows.columns or "status" not in rows.columns:
        return None

    return rows


def save_checksums(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    table_name: str,
    completed: dict[int, tuple[str, datetime]],
) -> None:
    """Persist checksums for successfully generated cohorts (v1 compat).

    .. deprecated:: 0.3.0
        Prefer ``save_generation_history()`` which stores the full generation
        record including status and start_time.  This wrapper is retained for
        backward compatibility and delegates internally.

    Args:
        backend: Ibis backend connection.
        schema: Schema/database where the table should be written.
        table_name: Name of the table.
        completed: Mapping of cohort_id -> (checksum, end_time) for cohorts
            that completed successfully in this run.
    """
    if not completed:
        return

    now = datetime.now()
    converted: dict[int, tuple[str, str, datetime, datetime]] = {}
    for cohort_id, (checksum, end_time) in completed.items():
        converted[cohort_id] = (checksum, "COMPLETE", now, end_time)

    save_generation_history(
        backend,
        schema=schema,
        table_name=table_name,
        generated=converted,
    )


def save_generation_history(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    table_name: str,
    generated: dict[int, tuple[str, str, datetime, datetime]],
) -> None:
    """Persist generation history for all generated cohorts (COMPLETE and FAILED).

    Uses the same read-filter-union-rewrite pattern as ``write_cohort`` so it
    works on every ibis backend without requiring raw SQL.

    Each row written to the table contains: ``(cohort_definition_id, checksum,
    status, start_time, end_time)``.  SKIPPED cohorts are intentionally
    omitted so their prior history entry is preserved.

    Args:
        backend: Ibis backend connection.
        schema: Schema/database where the table should be written.
        table_name: Name of the generation history table.
        generated: Mapping of cohort_id -> (checksum, status, start_time,
            end_time) for every cohort that was processed in this run
            (COMPLETE or FAILED).
    """
    if not generated:
        return

    import ibis
    import pandas as pd

    new_rows_df = pd.DataFrame(
        [
            {
                "cohort_definition_id": cohort_id,
                "checksum": checksum,
                "status": status,
                "start_time": start_time,
                "end_time": end_time,
            }
            for cohort_id, (checksum, status, start_time, end_time) in generated.items()
        ]
    )
    new_rows_df["cohort_definition_id"] = new_rows_df["cohort_definition_id"].astype("int64")
    new_rows_df["checksum"] = new_rows_df["checksum"].astype(str)
    new_rows_df["status"] = new_rows_df["status"].astype(str)
    new_rows_df["start_time"] = pd.to_datetime(new_rows_df["start_time"])
    new_rows_df["end_time"] = pd.to_datetime(new_rows_df["end_time"])

    new_relation = ibis.memtable(new_rows_df)

    if not table_exists(backend, table_name=table_name, schema=schema):
        create_table(backend, table_name=table_name, schema=schema, obj=new_relation, overwrite=False)
        return

    existing = read_table(backend, table_name=table_name, schema=schema)
    updated_ids = list(generated.keys())
    filtered_existing = existing.filter(
        ~existing.cohort_definition_id.cast("int64").isin(
            [ibis.literal(int(i), type="int64") for i in updated_ids]
        )
    )
    end_ts_type = existing.schema()["end_time"]
    start_ts_type = existing.schema()["start_time"]
    new_relation = new_relation.mutate(
        start_time=new_relation.start_time.cast(start_ts_type),
        end_time=new_relation.end_time.cast(end_ts_type),
    )
    merged = filtered_existing.union(new_relation, distinct=False)
    create_table(backend, table_name=table_name, schema=schema, obj=merged, overwrite=True)


def upsert_generation_history(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    table_name: str,
    cohort_id: int,
    checksum: str,
    status: str,
    start_time: datetime,
    end_time: datetime,
) -> None:
    """Persist the generation result for a single cohort.

    Unlike ``save_generation_history()`` this operates on one cohort at a
    time so that incremental persistence is possible — a completed cohort
    is recorded immediately rather than waiting for the entire batch to
    finish.

    Uses DELETE + INSERT (no full-table rewrite) so it is O(1) per call.

    Args:
        backend: Ibis backend connection.
        schema: Schema/database where the table lives.
        table_name: Name of the generation history table.
        cohort_id: Cohort definition id.
        checksum: Expression checksum for this generation.
        status: ``"COMPLETE"`` or ``"FAILED"``.
        start_time: When execution started.
        end_time: When execution ended.
    """
    import ibis
    import pandas as pd

    from ..execution.ibis.operations import (
        create_table,
        delete_cohort_rows,
        insert_relation,
        table_exists,
    )

    new_rows_df = pd.DataFrame(
        [
            {
                "cohort_definition_id": int(cohort_id),
                "checksum": str(checksum),
                "status": str(status),
                "start_time": pd.to_datetime(start_time),
                "end_time": pd.to_datetime(end_time),
            }
        ]
    )

    new_relation = ibis.memtable(new_rows_df)

    if not table_exists(backend, table_name=table_name, schema=schema):
        create_table(backend, table_name=table_name, schema=schema, obj=new_relation, overwrite=False)
        return

    delete_cohort_rows(
        backend,
        cohort_table=table_name,
        results_schema=schema,
        cohort_id=cohort_id,
    )
    insert_relation(
        new_relation,
        backend=backend,
        target_table=table_name,
        target_schema=schema,
    )
