"""Persistent definition registry and reuse checks for the runner.

The registry stores completion state per ``cohort_definition_id`` (checksum,
completion marker and row count).  It does not store definition JSON/SQL, which
keeps registry writes small and portable across data sources.

Identifier collisions (same id, different definition) are intentionally not
resolved yet.  They fail by default so a later identifier-mapping layer can be
added without silently corrupting another user's cohort.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import ibis

from ..execution.ibis.operations import (
    create_table,
    delete_rows,
    insert_rows_via_raw_sql,
    read_table,
    table_exists,
)
from ..execution.ibis_compat import literal_rows_relation
from ._core_types import CohortDefinitionLike

_REGISTRY_SCHEMA = {
    "cohort_definition_id": "int64",
    "cohort_name": "string",
    "definition_checksum": "string",
    "completed": "boolean",
    "row_count": "int64",
    "updated_at": "timestamp",
    "completed_at": "timestamp",
}
_REGISTRY_COLUMNS = list(_REGISTRY_SCHEMA)


class DefinitionRegistryError(ValueError):
    """Base error for registry/definition persistence checks."""


class DefinitionConflictError(DefinitionRegistryError):
    """Raised when a cohort id is reused with a different definition."""


@dataclass(frozen=True)
class RegistryEntry:
    cohort_definition_id: int
    definition_checksum: str
    completed: bool = False
    row_count: int | None = None


class DefinitionRegistry:
    """Small persistent registry of cohort completion state."""

    def __init__(
        self,
        backend: Any,
        *,
        schema: str,
        table_name: str,
        target_table: str,
    ) -> None:
        self.backend = backend
        self.schema = schema
        self.table_name = table_name
        self.target_table = target_table
        self._ensure_table()

    def _ensure_table(self) -> None:
        if table_exists(self.backend, table_name=self.table_name, schema=self.schema):
            return
        empty = literal_rows_relation([], schema=_REGISTRY_SCHEMA)
        create_table(
            self.backend,
            table_name=self.table_name,
            schema=self.schema,
            obj=empty,
            overwrite=False,
        )

    def entries(self) -> dict[int, RegistryEntry]:
        table = read_table(self.backend, table_name=self.table_name, schema=self.schema)
        rows = (
            table.select(
                "cohort_definition_id",
                "definition_checksum",
                "completed",
                "row_count",
            )
            .to_pyarrow()
            .to_pylist()
        )
        return {
            int(row["cohort_definition_id"]): RegistryEntry(
                cohort_definition_id=int(row["cohort_definition_id"]),
                definition_checksum=str(row["definition_checksum"]),
                completed=bool(row["completed"]),
                row_count=int(row["row_count"]) if row["row_count"] is not None else None,
            )
            for row in rows
        }

    def existing_target_counts(self) -> dict[int, int]:
        if not table_exists(self.backend, table_name=self.target_table, schema=self.schema):
            return {}
        table = read_table(self.backend, table_name=self.target_table, schema=self.schema)
        grouped = table.group_by("cohort_definition_id").aggregate(row_count=ibis._.count())
        rows = grouped.to_pyarrow().to_pylist()
        return {int(row["cohort_definition_id"]): int(row["row_count"]) for row in rows}

    def _write(
        self,
        definitions: list[CohortDefinitionLike],
        *,
        completed: bool,
        row_counts: dict[int, int] | None = None,
    ) -> None:
        if not definitions:
            return
        now = datetime.now()
        row_counts = row_counts or {}
        for definition in definitions:
            delete_rows(
                self.backend,
                table_name=self.table_name,
                schema=self.schema,
                column="cohort_definition_id",
                value=int(definition.cohort_id),
            )

        rows = []
        for definition in definitions:
            rows.append(
                [
                    int(definition.cohort_id),
                    str(definition.cohort_name),
                    definition.expression.checksum(),
                    bool(completed),
                    row_counts.get(int(definition.cohort_id), 0),
                    now,
                    now if completed else None,
                ]
            )

        for start in range(0, len(rows), 50):
            insert_rows_via_raw_sql(
                self.backend,
                table_name=self.table_name,
                schema=self.schema,
                columns=_REGISTRY_COLUMNS,
                rows=rows[start : start + 50],
            )

    def mark_incomplete(self, definitions: list[CohortDefinitionLike]) -> None:
        """Mark cohorts as in progress before generation starts.

        If generation or the copy into the cohort table fails, the next run
        sees ``completed=False`` and regenerates rather than reusing a partial
        write.
        """
        self._write(definitions, completed=False)

    def target_count(self, cohort_id: int) -> int:
        """Return the number of target rows for one cohort id."""
        if not table_exists(self.backend, table_name=self.target_table, schema=self.schema):
            return 0
        table = read_table(self.backend, table_name=self.target_table, schema=self.schema)
        value = table.filter(table.cohort_definition_id.cast("int64") == int(cohort_id)).count().execute()
        return int(value)

    def mark_complete(self, definition: CohortDefinitionLike) -> None:
        """Record one successfully generated cohort immediately."""
        cohort_id = int(definition.cohort_id)
        self._write(
            [definition],
            completed=True,
            row_counts={cohort_id: self.target_count(cohort_id)},
        )

    def upsert(self, definitions: list[CohortDefinitionLike]) -> None:
        """Record successfully generated/reused definitions with completion data."""
        self._write(
            definitions,
            completed=True,
            row_counts=self.existing_target_counts(),
        )

    def plan(
        self,
        definitions: list[CohortDefinitionLike],
        *,
        reuse_existing: bool,
        on_definition_change: str,
    ) -> tuple[list[CohortDefinitionLike], list[CohortDefinitionLike]]:
        """Return ``(to_generate, reused)`` and enforce id/definition safety."""
        existing = self.entries()
        target_counts = self.existing_target_counts() if reuse_existing else {}
        to_generate: list[CohortDefinitionLike] = []
        reused: list[CohortDefinitionLike] = []
        conflicts: list[tuple[int, str]] = []

        for definition in definitions:
            checksum = definition.expression.checksum()
            entry = existing.get(int(definition.cohort_id))
            if entry is not None and entry.definition_checksum != checksum:
                if on_definition_change == "error":
                    conflicts.append((int(definition.cohort_id), definition.cohort_name))
                else:
                    to_generate.append(definition)
                continue

            if (
                reuse_existing
                and entry is not None
                and entry.completed
                and entry.row_count is not None
                and target_counts.get(int(definition.cohort_id), 0) == entry.row_count
            ):
                reused.append(definition)
            else:
                to_generate.append(definition)

        if conflicts:
            details = ", ".join(f"{cohort_id} ({name})" for cohort_id, name in conflicts)
            raise DefinitionConflictError(
                "Cohort id(s) already exist with a different definition: "
                f"{details}. Identifier remapping is not implemented yet; "
                "use on_definition_change='replace' only when you own the id."
            )

        return to_generate, reused


__all__ = [
    "DefinitionConflictError",
    "DefinitionRegistry",
    "DefinitionRegistryError",
    "RegistryEntry",
]
