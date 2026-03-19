"""Custom era implementation using SQLGlot for cross-dialect compatibility.

This module implements custom era logic (gap-based event grouping with offsets)
using a reference SQL implementation that is transpiled to target dialects via SQLGlot.

The custom era strategy groups events by person_id and creates "eras" where events
are grouped together if they occur within gap_days of each other. Each era can have
start and end offsets applied.

Example:
    Given events on days [1, 3, 10, 12] with gap_days=5:
    - Era 1: days 1-3 (within 5 days)
    - Era 2: days 10-12 (within 5 days)
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import sqlglot

from ..errors import CompilationError, UnsupportedFeatureError
from ..plan.schema import END_DATE, PERSON_ID, START_DATE

if TYPE_CHECKING:
    from ..typing import IbisBackendLike


# Mapping of Ibis backend names to SQLGlot dialect names
BACKEND_DIALECT_MAP = {
    "duckdb": "duckdb",
    "postgres": "postgres",
    "spark": "spark",
    "databricks": "databricks",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
    "trino": "trino",
    "mysql": "mysql",
    "sqlite": "sqlite",
}


def get_backend_dialect(backend: IbisBackendLike) -> str:
    """Get SQLGlot dialect name from Ibis backend.

    Args:
        backend: Ibis backend instance

    Returns:
        SQLGlot dialect name

    Raises:
        UnsupportedFeatureError: If backend is not supported for custom era
    """
    backend_name = backend.name.lower()

    # Handle special cases
    if "databricks" in backend_name or "spark" in backend_name:
        return "databricks"

    dialect = BACKEND_DIALECT_MAP.get(backend_name)
    if dialect is None:
        raise UnsupportedFeatureError(
            f"Custom era not supported for backend: {backend_name}. "
            f"Supported backends: {', '.join(BACKEND_DIALECT_MAP.keys())}"
        )

    return dialect


def generate_custom_era_sql_reference(
    events_table_name: str,
    gap_days: int,
    offset_start: int = 0,
    offset_end: int = 0,
) -> str:
    """Generate reference custom era SQL in PostgreSQL dialect.

    This is the "golden" implementation that gets transpiled to other dialects.
    PostgreSQL is chosen as the reference because it has the most standard SQL
    syntax for window functions and date arithmetic.

    The logic:
    1. Compute LAG(start_date) for each person's events
    2. Mark new era boundaries where gap > gap_days
    3. Assign era IDs using cumulative sum
    4. Group by person + era and compute era bounds with offsets

    Args:
        events_table_name: Fully qualified events table (e.g., "schema.events")
        gap_days: Maximum days between events in same era
        offset_start: Days to subtract from era start (can be negative)
        offset_end: Days to add to era end (can be negative)

    Returns:
        PostgreSQL SQL query as string
    """
    # Use triple-quoted f-string for readability
    sql = f"""
    WITH event_gaps AS (
      SELECT *,
        LAG({START_DATE}) OVER (
          PARTITION BY {PERSON_ID} 
          ORDER BY {START_DATE}
        ) AS prev_start_date
      FROM {events_table_name}
    ),
    era_boundaries AS (
      SELECT *,
        CASE 
          WHEN prev_start_date IS NULL THEN 1
          WHEN {START_DATE} - prev_start_date > INTERVAL '{gap_days} days' THEN 1
          ELSE 0
        END AS is_new_era
      FROM event_gaps
    ),
    era_ids AS (
      SELECT *,
        SUM(is_new_era) OVER (
          PARTITION BY {PERSON_ID} 
          ORDER BY {START_DATE}
          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS era_id
      FROM era_boundaries
    ),
    eras AS (
      SELECT 
        {PERSON_ID},
        era_id,
        MIN({START_DATE}) - INTERVAL '{offset_start} days' AS era_start,
        MAX({END_DATE}) + INTERVAL '{offset_end} days' AS era_end
      FROM era_ids
      GROUP BY {PERSON_ID}, era_id
    )
    SELECT 
      {PERSON_ID},
      era_start AS {START_DATE},
      era_end AS {END_DATE}
    FROM eras
    ORDER BY {PERSON_ID}, {START_DATE}
    """

    return sql.strip()


def transpile_custom_era_sql(
    reference_sql: str,
    target_dialect: str,
) -> str:
    """Transpile reference PostgreSQL SQL to target dialect using SQLGlot.

    Args:
        reference_sql: Custom era SQL in PostgreSQL syntax
        target_dialect: Target SQL dialect (e.g., "spark", "duckdb")

    Returns:
        Transpiled SQL for target dialect

    Raises:
        CompilationError: If transpilation fails
    """
    try:
        # Parse and transpile
        transpiled = sqlglot.transpile(
            reference_sql,
            read="postgres",
            write=target_dialect,
            pretty=True,
        )

        if not transpiled:
            raise CompilationError(f"SQLGlot transpilation produced no output for dialect: {target_dialect}")

        return transpiled[0]

    except Exception as exc:
        raise CompilationError(f"Failed to transpile custom era SQL to {target_dialect}: {exc}") from exc


def build_custom_era_sql(
    backend: IbisBackendLike,
    events_table_name: str,
    gap_days: int,
    offset_start: int = 0,
    offset_end: int = 0,
    debug: bool = False,
) -> str:
    """Build custom era SQL for a specific backend using SQLGlot transpilation.

    Args:
        backend: Ibis backend instance
        events_table_name: Fully qualified events table name
        gap_days: Maximum days between events in same era
        offset_start: Days to subtract from era start
        offset_end: Days to add to era end
        debug: If True, print reference and transpiled SQL

    Returns:
        Transpiled custom era SQL for the backend's dialect

    Raises:
        UnsupportedFeatureError: If backend doesn't support custom era
        CompilationError: If SQL generation or transpilation fails
    """
    # Validate parameters
    if gap_days < 0:
        raise CompilationError(f"gap_days must be non-negative, got: {gap_days}")

    # Get target dialect
    target_dialect = get_backend_dialect(backend)

    # Generate reference SQL
    reference_sql = generate_custom_era_sql_reference(
        events_table_name=events_table_name,
        gap_days=gap_days,
        offset_start=offset_start,
        offset_end=offset_end,
    )

    if debug:
        print("=== Reference SQL (PostgreSQL) ===")
        print(reference_sql)
        print()

    # Transpile to target dialect
    transpiled_sql = transpile_custom_era_sql(reference_sql, target_dialect)

    if debug:
        print(f"=== Transpiled SQL ({target_dialect}) ===")
        print(transpiled_sql)
        print()

    return transpiled_sql


def apply_custom_era(
    backend: IbisBackendLike,
    events,
    gap_days: int,
    offset_start: int = 0,
    offset_end: int = 0,
    schema: str | None = None,
    debug: bool = False,
):
    """Apply custom era strategy to events using SQLGlot-transpiled SQL.

    This function:
    1. Materializes events to a temporary table
    2. Generates custom era SQL via SQLGlot transpilation
    3. Executes the SQL to produce era-grouped events
    4. Returns the result as an Ibis table expression

    Args:
        backend: Ibis backend instance
        events: Ibis table expression of events (must have person_id, start_date, end_date)
        gap_days: Maximum days between events in same era
        offset_start: Days to subtract from era start
        offset_end: Days to add to era end
        schema: Schema for temporary table (optional)
        debug: If True, print generated SQL

    Returns:
        Ibis table expression with custom eras applied

    Raises:
        UnsupportedFeatureError: If backend doesn't support custom era
        CompilationError: If SQL generation fails
    """
    # Create a temporary table name
    temp_table_name = f"_custom_era_events_{id(events)}"
    full_table_name = f"{schema}.{temp_table_name}" if schema else temp_table_name

    # Materialize events to temporary table
    # Note: Some backends may not support CREATE TEMP TABLE, adjust as needed
    try:
        backend.create_table(temp_table_name, events, schema=schema, temp=True)
    except Exception:
        # Fallback: try without temp=True
        backend.create_table(temp_table_name, events, schema=schema, overwrite=True)

    try:
        # Generate custom era SQL
        era_sql = build_custom_era_sql(
            backend=backend,
            events_table_name=full_table_name,
            gap_days=gap_days,
            offset_start=offset_start,
            offset_end=offset_end,
            debug=debug,
        )

        # Execute SQL and return as Ibis table
        eras = backend.sql(era_sql)

        return eras

    finally:
        # Clean up temporary table
        with contextlib.suppress(Exception):
            backend.drop_table(temp_table_name, schema=schema, force=True)


def validate_custom_era_support(backend: IbisBackendLike) -> bool:
    """Check if backend supports custom era implementation.

    Args:
        backend: Ibis backend instance

    Returns:
        True if custom era is supported for this backend
    """
    backend_name = backend.name.lower()
    return backend_name in BACKEND_DIALECT_MAP or "databricks" in backend_name or "spark" in backend_name
