"""Session-activity registry for detecting orphaned staging tables.

The experimental Ibis execution engine creates persistent staging tables
(``<prefix>__staging_*`` and ``<prefix>__codesets``) that are cleaned up at the
end of ``write_cohort`` / batch generation.  If the process or connection dies
mid-build, those tables are left behind.

To let users discover (and optionally reclaim) them, each build records its
session prefix in a small registry table (``_circe_session``) with a creation
timestamp.  :func:`list_stale_sessions` reports registrations older than a
threshold whose staging tables still exist, and :func:`cleanup_stale_sessions`
drops them.
"""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from .ibis.operations import (
    create_table,
    delete_rows,
    insert_rows_via_raw_sql,
    read_table,
    table_exists,
)

if TYPE_CHECKING:
    from .typing import IbisBackendLike

logger = logging.getLogger(__name__)

SESSION_TABLE = "_circe_session"


@dataclass(frozen=True)
class StaleSession:
    """A registered session whose staging tables outlived the threshold."""

    session_prefix: str
    created_at: Any
    tables: tuple[str, ...]


def _default_threshold() -> timedelta:
    raw = os.environ.get("CIRCE_STALE_SESSION_DAYS")
    if raw:
        try:
            return timedelta(days=float(raw))
        except ValueError:
            logger.warning("Invalid CIRCE_STALE_SESSION_DAYS=%r; using 7 days.", raw)
    return timedelta(weeks=1)


def _list_tables(backend: IbisBackendLike, schema: str | None) -> list[str]:
    try:
        if schema is not None:
            return list(backend.list_tables(database=schema))
        return list(backend.list_tables())
    except TypeError:
        return list(backend.list_tables())


def _upsert_session(
    backend: IbisBackendLike,
    schema: str | None,
    session_prefix: str,
    now: datetime,
) -> None:
    import ibis

    if not table_exists(backend, table_name=SESSION_TABLE, schema=schema):
        row = (
            ibis.literal(str(session_prefix), type="str")
            .name("session_prefix")
            .as_table()
            .mutate(created_at=ibis.literal(now, type="timestamp"))
        )
        create_table(backend, table_name=SESSION_TABLE, schema=schema, obj=row, overwrite=False)
        return

    delete_rows(
        backend,
        table_name=SESSION_TABLE,
        schema=schema,
        column="session_prefix",
        value=str(session_prefix),
    )
    insert_rows_via_raw_sql(
        backend,
        table_name=SESSION_TABLE,
        schema=schema,
        columns=["session_prefix", "created_at"],
        rows=[[str(session_prefix), now]],
    )


def register_session(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    session_prefix: str,
    now: datetime | None = None,
) -> None:
    """Record *session_prefix* in the session registry with a creation time.

    Best-effort: a failure to write the registry is logged and swallowed so it
    never fails cohort generation.
    """
    try:
        _upsert_session(backend, schema, session_prefix, now or datetime.now())
    except Exception:
        logger.warning("Failed to register session '%s'", session_prefix, exc_info=True)


def unregister_session(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    session_prefix: str,
) -> None:
    """Remove *session_prefix* from the session registry.

    Best-effort: a failure is logged and swallowed.
    """
    try:
        if table_exists(backend, table_name=SESSION_TABLE, schema=schema):
            delete_rows(
                backend,
                table_name=SESSION_TABLE,
                schema=schema,
                column="session_prefix",
                value=str(session_prefix),
            )
    except Exception:
        logger.warning("Failed to unregister session '%s'", session_prefix, exc_info=True)


def list_stale_sessions(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    older_than: timedelta | None = None,
) -> list[StaleSession]:
    """Return registered sessions older than *older_than* whose tables remain.

    Registrations whose staging tables no longer exist are pruned from the
    registry and not returned.
    """
    threshold = older_than or _default_threshold()

    if not table_exists(backend, table_name=SESSION_TABLE, schema=schema):
        return []

    import ibis

    table = read_table(backend, table_name=SESSION_TABLE, schema=schema)
    cutoff = datetime.now() - threshold
    stale_rows = table.filter(table.created_at < ibis.literal(cutoff, type="timestamp")).execute()

    tables_in_schema = _list_tables(backend, schema)
    results: list[StaleSession] = []
    for record in stale_rows.to_dict(orient="records"):
        prefix = str(record["session_prefix"])
        remaining = tuple(sorted(t for t in tables_in_schema if t.startswith(prefix)))
        if remaining:
            results.append(
                StaleSession(
                    session_prefix=prefix,
                    created_at=record["created_at"],
                    tables=remaining,
                )
            )
        else:
            unregister_session(backend, schema=schema, session_prefix=prefix)
    return results


def report_stale_sessions(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    older_than: timedelta | None = None,
) -> list[StaleSession]:
    """Log a warning for stale staging tables and return the list.

    Best-effort: any error while checking is logged at debug level and an empty
    list is returned, so this can be used as a no-op guard at build time.
    """
    threshold = older_than or _default_threshold()
    try:
        stale = list_stale_sessions(backend, schema=schema, older_than=threshold)
    except Exception:
        logger.debug("Failed checking for stale session tables", exc_info=True)
        return []
    if stale:
        logger.warning(_format_report(stale, schema, threshold))
    return stale


def cleanup_stale_sessions(
    backend: IbisBackendLike,
    *,
    schema: str | None,
    older_than: timedelta | None = None,
) -> list[str]:
    """Drop stale staging tables and unregister their sessions.

    Returns the names of the tables dropped.
    """
    stale = list_stale_sessions(backend, schema=schema, older_than=older_than)
    dropped: list[str] = []
    for session in stale:
        for table in session.tables:
            with contextlib.suppress(Exception):
                backend.drop_table(table, database=schema, force=True)
            dropped.append(table)
        unregister_session(backend, schema=schema, session_prefix=session.session_prefix)
    return dropped


def _format_report(stale: list[StaleSession], schema: str | None, threshold: timedelta) -> str:
    schema_label = schema if schema is not None else "<default>"
    lines = [
        f"{len(stale)} stale Circe staging table group(s) older than "
        f"{threshold.days} days found in schema '{schema_label}':"
    ]
    for session in stale:
        lines.append(
            f"  - {session.session_prefix} (created {session.created_at}): " + ", ".join(session.tables)
        )
    lines.append("Consider running cleanup_stale_sessions() to drop them.")
    return "\n".join(lines)
