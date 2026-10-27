"""Persistent definition registry and reuse checks for the runner.

The registry stores the latest definition per ``cohort_definition_id``.  It is
what makes a shared, persistent cohort table usable by multiple users: rows for
other cohort ids are never touched, and a rerun can skip cohorts whose
definition checksum and target rows are already present.

Identifier collisions (same id, different definition) are intentionally not
resolved yet.  They fail by default so a later identifier-mapping layer can be
added without silently corrupting another user's cohort.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..execution.ibis.operations import (
    create_table,
    delete_rows,
    insert_rows_via_raw_sql,
    read_table,
    table_exists,
)
from ..execution.ibis_compat import literal_rows_relation
from ._core_types import CohortDefinitionLike

logger = logging.getLogger(__name__)

_REGISTRY_SCHEMA = {
    "cohort_definition_id": "int64",
    "cohort_name": "string",
    "definition_checksum": "string",
    "definition_json": "string",
    "sql": "string",
    "metadata_json": "string",
    "updated_at": "timestamp",
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


class DefinitionRegistry:
    """Small persistent registry of cohort definitions."""

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
        rows = table.select("cohort_definition_id", "definition_checksum").to_pyarrow().to_pylist()
        return {
            int(row["cohort_definition_id"]): RegistryEntry(
                cohort_definition_id=int(row["cohort_definition_id"]),
                definition_checksum=str(row["definition_checksum"]),
            )
            for row in rows
        }

    def existing_target_ids(self) -> set[int]:
        if not table_exists(self.backend, table_name=self.target_table, schema=self.schema):
            return set()
        table = read_table(self.backend, table_name=self.target_table, schema=self.schema)
        rows = table.select("cohort_definition_id").distinct().to_pyarrow().to_pylist()
        return {int(row["cohort_definition_id"]) for row in rows}

    def upsert(self, definitions: list[CohortDefinitionLike]) -> None:
        if not definitions:
            return
        now = datetime.now()
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
            metadata = getattr(definition, "metadata", {}) or {}
            source = getattr(definition, "source", None)
            if source is not None:
                metadata = {
                    **metadata,
                    "_json_file": str(source.json_file),
                    "_sql_file": str(source.sql_file) if source.sql_file else None,
                }
            rows.append(
                [
                    int(definition.cohort_id),
                    str(definition.cohort_name),
                    definition.expression.checksum(),
                    definition.expression.model_dump_json(by_alias=True),
                    getattr(definition, "sql", None),
                    json.dumps(metadata, sort_keys=True, default=str),
                    now,
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

    def plan(
        self,
        definitions: list[CohortDefinitionLike],
        *,
        reuse_existing: bool,
        on_definition_change: str,
    ) -> tuple[list[CohortDefinitionLike], list[CohortDefinitionLike]]:
        """Return ``(to_generate, reused)`` and enforce id/definition safety."""
        existing = self.entries()
        target_ids = self.existing_target_ids() if reuse_existing else set()
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

            if reuse_existing and entry is not None and int(definition.cohort_id) in target_ids:
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
