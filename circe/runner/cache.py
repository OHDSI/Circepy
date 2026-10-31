"""Checksum-keyed cohort cache and final integer-id projection.

Generation writes each cohort once into ``cache_table`` keyed by the canonical
definition checksum.  The study-facing cohort table is populated only in a
second, copy-only phase using the integer cohort ids from the request.
"""

from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import ibis

from ..cohort_definition_set import CohortDefinition, CohortDefinitionSet, generate_cohort_set
from ..decomposition import semantic_expression_key
from ..execution.ibis.operations import (
    create_table,
    delete_rows,
    insert_relation,
    insert_rows_via_raw_sql,
    read_table,
    table_exists,
)
from ..execution.ibis_compat import literal_rows_relation
from ..execution.session import register_session, unregister_session

_CACHE_ROWS_SCHEMA = {
    "cohort_checksum": "string",
    "subject_id": "int64",
    "cohort_start_date": "date",
    "cohort_end_date": "date",
}
_CACHE_REGISTRY_SCHEMA = {
    "cohort_checksum": "string",
    "completed": "boolean",
    "row_count": "int64",
    "updated_at": "timestamp",
    "completed_at": "timestamp",
}
_OUTPUT_SCHEMA = {
    "cohort_definition_id": "int64",
    "subject_id": "int64",
    "cohort_start_date": "date",
    "cohort_end_date": "date",
}
_CACHE_REGISTRY_COLUMNS = list(_CACHE_REGISTRY_SCHEMA)


def cohort_checksum(expression: Any) -> str:
    """Return the canonical checksum used as the cache identity."""
    return semantic_expression_key(expression, include_title=False)


@dataclass(frozen=True)
class CacheEntry:
    cohort_checksum: str
    completed: bool
    row_count: int | None


@dataclass
class CacheBuildOutcome:
    generated: list[int] = field(default_factory=list)
    reused: list[int] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)


class CohortCache:
    """Checksum-keyed cached cohort rows and completion registry."""

    def __init__(
        self,
        backend: Any,
        *,
        schema: str,
        table_name: str,
        registry_table: str,
    ) -> None:
        self.backend = backend
        self.schema = schema
        self.table_name = table_name
        self.registry_table = registry_table
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        if not table_exists(self.backend, table_name=self.table_name, schema=self.schema):
            create_table(
                self.backend,
                table_name=self.table_name,
                schema=self.schema,
                obj=literal_rows_relation([], schema=_CACHE_ROWS_SCHEMA),
                overwrite=False,
            )
        if not table_exists(self.backend, table_name=self.registry_table, schema=self.schema):
            create_table(
                self.backend,
                table_name=self.registry_table,
                schema=self.schema,
                obj=literal_rows_relation([], schema=_CACHE_REGISTRY_SCHEMA),
                overwrite=False,
            )

    def entries(self) -> dict[str, CacheEntry]:
        table = read_table(self.backend, table_name=self.registry_table, schema=self.schema)
        rows = table.select("cohort_checksum", "completed", "row_count").to_pyarrow().to_pylist()
        return {
            str(row["cohort_checksum"]): CacheEntry(
                cohort_checksum=str(row["cohort_checksum"]),
                completed=bool(row["completed"]),
                row_count=int(row["row_count"]) if row["row_count"] is not None else None,
            )
            for row in rows
        }

    def count_rows(self, checksum: str) -> int:
        if not table_exists(self.backend, table_name=self.table_name, schema=self.schema):
            return 0
        table = read_table(self.backend, table_name=self.table_name, schema=self.schema)
        return int(table.filter(table.cohort_checksum == checksum).count().execute())

    def mark_incomplete(self, checksums: list[str]) -> None:
        self._write_registry(checksums, completed=False, counts={})

    def mark_complete(self, checksum: str, row_count: int) -> None:
        self._write_registry([checksum], completed=True, counts={checksum: row_count})

    def _write_registry(
        self,
        checksums: list[str],
        *,
        completed: bool,
        counts: dict[str, int],
    ) -> None:
        if not checksums:
            return
        now = datetime.now()
        for checksum in checksums:
            delete_rows(
                self.backend,
                table_name=self.registry_table,
                schema=self.schema,
                column="cohort_checksum",
                value=checksum,
            )
        rows = [
            [
                checksum,
                bool(completed),
                counts.get(checksum, 0),
                now,
                now if completed else None,
            ]
            for checksum in checksums
        ]
        insert_rows_via_raw_sql(
            self.backend,
            table_name=self.registry_table,
            schema=self.schema,
            columns=_CACHE_REGISTRY_COLUMNS,
            rows=rows,
        )

    def copy_from_staging(
        self,
        *,
        staging_table: str,
        internal_id: int,
        checksum: str,
    ) -> int:
        staged = read_table(
            self.backend,
            table_name=staging_table,
            schema=self.schema,
        )
        selected = staged.filter(staged.cohort_definition_id == int(internal_id)).select(
            cohort_checksum=ibis.literal(checksum),
            subject_id=staged.subject_id,
            cohort_start_date=staged.cohort_start_date,
            cohort_end_date=staged.cohort_end_date,
        )
        count = int(selected.count().execute())
        delete_rows(
            self.backend,
            table_name=self.table_name,
            schema=self.schema,
            column="cohort_checksum",
            value=checksum,
        )
        insert_relation(
            selected,
            backend=self.backend,
            target_table=self.table_name,
            target_schema=self.schema,
        )
        return count

    def copy_to_output(
        self,
        *,
        output_table: str,
        output_schema: str,
        cohort_id: int,
        checksum: str,
    ) -> int:
        cached = read_table(self.backend, table_name=self.table_name, schema=self.schema)
        selected = cached.filter(cached.cohort_checksum == checksum).select(
            cohort_definition_id=ibis.literal(int(cohort_id)),
            subject_id=cached.subject_id,
            cohort_start_date=cached.cohort_start_date,
            cohort_end_date=cached.cohort_end_date,
        )
        count = int(selected.count().execute())
        delete_rows(
            self.backend,
            table_name=output_table,
            schema=output_schema,
            column="cohort_definition_id",
            value=int(cohort_id),
        )
        insert_relation(
            selected,
            backend=self.backend,
            target_table=output_table,
            target_schema=output_schema,
        )
        return count


def ensure_output_table(
    backend: Any,
    *,
    schema: str,
    table: str,
) -> None:
    if table_exists(backend, table_name=table, schema=schema):
        return
    create_table(
        backend,
        table_name=table,
        schema=schema,
        obj=literal_rows_relation([], schema=_OUTPUT_SCHEMA),
        overwrite=False,
    )


def _family_key(definition: CohortDefinition) -> str:
    return (definition.family or "").strip() or f"__cohort_{definition.cohort_id}"


def build_cache(
    backend: Any,
    cache: CohortCache,
    definitions: list[CohortDefinition],
    *,
    cdm_schema: str,
    vocabulary_schema: str | None,
    shared: bool,
    reuse_existing: bool = True,
) -> CacheBuildOutcome:
    """Generate missing checksums into the cache, family by family."""
    outcome = CacheBuildOutcome()
    checksums = {definition.cohort_id: cohort_checksum(definition.expression) for definition in definitions}
    ids_by_checksum: dict[str, list[int]] = {}
    representative: dict[str, CohortDefinition] = {}
    for definition in definitions:
        checksum = checksums[definition.cohort_id]
        ids_by_checksum.setdefault(checksum, []).append(definition.cohort_id)
        representative.setdefault(checksum, definition)

    existing = cache.entries()
    missing_checksums: list[str] = []
    for checksum, _definition in representative.items():
        entry = existing.get(checksum)
        reusable = (
            reuse_existing
            and entry is not None
            and entry.completed
            and entry.row_count is not None
            and cache.count_rows(checksum) == entry.row_count
        )
        if reusable:
            outcome.reused.extend(ids_by_checksum[checksum])
        else:
            missing_checksums.append(checksum)

    if not missing_checksums:
        return outcome

    cache.mark_incomplete(missing_checksums)
    families: dict[str, list[str]] = {}
    for checksum in missing_checksums:
        definition = representative[checksum]
        families.setdefault(_family_key(definition), []).append(checksum)

    for family, family_checksums in families.items():
        staging_table = f"__cache_stage_{uuid.uuid4().hex[:8]}"
        internal: dict[int, str] = {}
        subset = CohortDefinitionSet()
        for index, checksum in enumerate(family_checksums, start=1):
            definition = representative[checksum]
            internal[index] = checksum
            subset.add_definition(
                CohortDefinition(
                    cohort_id=index,
                    cohort_name=definition.cohort_name,
                    expression=definition.expression,
                    family=definition.family,
                )
            )

        register_session(
            backend,
            schema=cache.schema,
            session_prefix=staging_table,
        )

        def _on_complete(
            result: Any,
            *,
            internal: dict[int, str] = internal,
            staging_table: str = staging_table,
        ) -> None:
            checksum = internal[int(result.cohort_id)]
            count = cache.copy_from_staging(
                staging_table=staging_table,
                internal_id=int(result.cohort_id),
                checksum=checksum,
            )
            cache.mark_complete(checksum, count)
            outcome.generated.extend(ids_by_checksum[checksum])

        try:
            generate_cohort_set(
                subset,
                backend=backend,
                cdm_schema=cdm_schema,
                vocabulary_schema=vocabulary_schema,
                results_schema=cache.schema,
                cohort_table=staging_table,
                shared=shared,
                on_cohort_complete=_on_complete,
            )
        except Exception as exc:  # noqa: BLE001 - one family must not stop the rest
            outcome.failed.append({"family": family, "error": f"{type(exc).__name__}: {exc}"})
        finally:
            with contextlib.suppress(Exception):
                backend.drop_table(staging_table, database=cache.schema, force=True)
            unregister_session(
                backend,
                schema=cache.schema,
                session_prefix=staging_table,
            )
    return outcome


def copy_cache_to_output(
    backend: Any,
    cache: CohortCache,
    definitions: list[CohortDefinition],
    *,
    output_schema: str,
    output_table: str,
) -> CacheBuildOutcome:
    """Copy cached checksums into the integer-id output table."""
    outcome = CacheBuildOutcome()
    entries = cache.entries()
    for definition in definitions:
        checksum = cohort_checksum(definition.expression)
        entry = entries.get(checksum)
        if entry is None or not entry.completed:
            outcome.failed.append({"family": _family_key(definition), "error": f"cache miss for {checksum}"})
            continue
        try:
            cache.copy_to_output(
                output_table=output_table,
                output_schema=output_schema,
                cohort_id=int(definition.cohort_id),
                checksum=checksum,
            )
            outcome.generated.append(definition.cohort_id)
        except Exception as exc:  # noqa: BLE001
            outcome.failed.append(
                {"family": _family_key(definition), "error": f"{type(exc).__name__}: {exc}"}
            )
    return outcome


__all__ = [
    "CacheBuildOutcome",
    "CacheEntry",
    "CohortCache",
    "build_cache",
    "cohort_checksum",
    "copy_cache_to_output",
    "ensure_output_table",
]
