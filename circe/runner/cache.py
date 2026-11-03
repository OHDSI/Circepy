"""Checksum-keyed cohort cache and final integer-id projection.

Generation writes each cohort once into ``cache_table`` keyed by the canonical
definition checksum.  The study-facing cohort table is populated only in a
second, copy-only phase using the integer cohort ids from the request.
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import ibis

from ..cohort_definition_set import CohortDefinition, CohortDefinitionSet, generate_cohort_set
from ..decomposition import cohort_checksum
from ..execution.ibis.operations import (
    create_table,
    delete_rows_in,
    insert_relation,
    insert_rows_via_raw_sql,
    read_table,
    table_exists,
)
from ..execution.ibis_compat import literal_rows_relation
from ..execution.session import register_session, unregister_session

logger = logging.getLogger(__name__)

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
_OUTPUT_MAP_SCHEMA = {
    "cohort_definition_id": "int64",
    "cohort_checksum": "string",
    "row_count": "int64",
    "completed": "boolean",
    "updated_at": "timestamp",
    "completed_at": "timestamp",
}
_OUTPUT_MAP_COLUMNS = list(_OUTPUT_MAP_SCHEMA)
_CACHE_REGISTRY_COLUMNS = list(_CACHE_REGISTRY_SCHEMA)


def _mapping_relation(rows: list[dict[str, Any]]) -> Any:
    """Build a small mapping relation without a recursive union chain."""
    schema = ibis.schema({"cohort_definition_id": "int64", "cohort_checksum": "string"})
    return ibis.memtable(
        {
            "cohort_definition_id": [int(row["cohort_definition_id"]) for row in rows],
            "cohort_checksum": [str(row["cohort_checksum"]) for row in rows],
        },
        schema=schema,
    )


@dataclass(frozen=True)
class CacheEntry:
    cohort_checksum: str
    completed: bool
    row_count: int | None


@dataclass(frozen=True)
class OutputCopyEntry:
    cohort_definition_id: int
    cohort_checksum: str
    row_count: int | None
    completed: bool


class OutputCopyMap:
    """Tracks which integer-id outputs have already been copied from cache."""

    def __init__(self, backend: Any, *, schema: str, table_name: str) -> None:
        self.backend = backend
        self.schema = schema
        self.table_name = table_name
        self._ensure()

    def _ensure(self) -> None:
        if table_exists(self.backend, table_name=self.table_name, schema=self.schema):
            return
        create_table(
            self.backend,
            table_name=self.table_name,
            schema=self.schema,
            obj=literal_rows_relation([], schema=_OUTPUT_MAP_SCHEMA),
            overwrite=False,
        )

    def entries(self) -> dict[int, OutputCopyEntry]:
        table = read_table(self.backend, table_name=self.table_name, schema=self.schema)
        rows = (
            table.select(
                "cohort_definition_id",
                "cohort_checksum",
                "row_count",
                "completed",
            )
            .to_pyarrow()
            .to_pylist()
        )
        return {
            int(row["cohort_definition_id"]): OutputCopyEntry(
                cohort_definition_id=int(row["cohort_definition_id"]),
                cohort_checksum=str(row["cohort_checksum"]),
                row_count=int(row["row_count"]) if row["row_count"] is not None else None,
                completed=bool(row["completed"]),
            )
            for row in rows
        }

    def mark_complete(self, rows: list[tuple[int, str, int]]) -> None:
        if not rows:
            return
        ids = [row[0] for row in rows]
        delete_rows_in(
            self.backend,
            table_name=self.table_name,
            schema=self.schema,
            column="cohort_definition_id",
            values=ids,
        )
        now = datetime.now()
        insert_rows_via_raw_sql(
            self.backend,
            table_name=self.table_name,
            schema=self.schema,
            columns=_OUTPUT_MAP_COLUMNS,
            rows=[[cohort_id, checksum, count, True, now, now] for cohort_id, checksum, count in rows],
        )


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

    def counts(self, checksums: list[str]) -> dict[str, int]:
        """Count cache rows for several checksums in one query."""
        if not checksums:
            return {}
        table = read_table(self.backend, table_name=self.table_name, schema=self.schema)
        grouped = (
            table.filter(table.cohort_checksum.isin(checksums))
            .group_by("cohort_checksum")
            .aggregate(row_count=ibis._.count())
        )
        return {
            str(row["cohort_checksum"]): int(row["row_count"]) for row in grouped.to_pyarrow().to_pylist()
        }

    def mark_incomplete(self, checksums: list[str]) -> None:
        self._write_registry(checksums, completed=False, counts={})

    def mark_complete(self, checksum: str, row_count: int) -> None:
        self.mark_complete_many({checksum: row_count})

    def mark_complete_many(self, counts: dict[str, int]) -> None:
        self._write_registry(list(counts), completed=True, counts=counts)

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
        delete_rows_in(
            self.backend,
            table_name=self.registry_table,
            schema=self.schema,
            column="cohort_checksum",
            values=list(checksums),
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

    def copy_family_from_staging(
        self,
        *,
        staging_table: str,
        internal_checksums: dict[int, str],
    ) -> dict[str, int]:
        """Copy one family from staging with one join and grouped counts."""
        staged = read_table(self.backend, table_name=staging_table, schema=self.schema)
        grouped = (
            staged.group_by("cohort_definition_id")
            .aggregate(row_count=ibis._.count())
            .to_pyarrow()
            .to_pylist()
        )
        counts_by_internal = {int(row["cohort_definition_id"]): int(row["row_count"]) for row in grouped}
        counts = {
            checksum: counts_by_internal.get(internal_id, 0)
            for internal_id, checksum in internal_checksums.items()
        }

        mapping = _mapping_relation(
            [
                {"cohort_definition_id": internal_id, "cohort_checksum": checksum}
                for internal_id, checksum in internal_checksums.items()
            ]
        )
        relation = mapping.join(staged, mapping.cohort_definition_id == staged.cohort_definition_id).select(
            cohort_checksum=mapping.cohort_checksum,
            subject_id=staged.subject_id,
            cohort_start_date=staged.cohort_start_date,
            cohort_end_date=staged.cohort_end_date,
        )
        checksums = list(internal_checksums.values())
        delete_rows_in(
            self.backend,
            table_name=self.table_name,
            schema=self.schema,
            column="cohort_checksum",
            values=checksums,
        )
        insert_relation(
            relation,
            backend=self.backend,
            target_table=self.table_name,
            target_schema=self.schema,
        )
        return counts


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
    completed_checksums = [
        checksum
        for checksum, entry in existing.items()
        if reuse_existing and entry.completed and entry.row_count is not None
    ]
    actual_counts = cache.counts(completed_checksums) if completed_checksums else {}
    missing_checksums: list[str] = []
    for checksum in representative:
        entry = existing.get(checksum)
        reusable = (
            reuse_existing
            and entry is not None
            and entry.completed
            and entry.row_count is not None
            and actual_counts.get(checksum, 0) == entry.row_count
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

        try:
            generate_cohort_set(
                subset,
                backend=backend,
                cdm_schema=cdm_schema,
                vocabulary_schema=vocabulary_schema,
                results_schema=cache.schema,
                cohort_table=staging_table,
                shared=shared,
            )
            counts = cache.copy_family_from_staging(
                staging_table=staging_table,
                internal_checksums=internal,
            )
            cache.mark_complete_many(counts)
            for checksum in family_checksums:
                outcome.generated.extend(ids_by_checksum[checksum])
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
    output_registry_table: str = "cohort_output_map",
) -> CacheBuildOutcome:
    """Copy cached checksums into the integer-id output table in one pass."""
    outcome = CacheBuildOutcome()
    cache_entries = cache.entries()
    output_map = OutputCopyMap(backend, schema=output_schema, table_name=output_registry_table)
    existing_copies = output_map.entries()
    to_copy: list[tuple[int, str, int]] = []

    for definition in definitions:
        checksum = cohort_checksum(definition.expression)
        cache_entry = cache_entries.get(checksum)
        if cache_entry is None or not cache_entry.completed or cache_entry.row_count is None:
            outcome.failed.append({"family": _family_key(definition), "error": f"cache miss for {checksum}"})
            continue
        copied = existing_copies.get(int(definition.cohort_id))
        if (
            copied is not None
            and copied.completed
            and copied.cohort_checksum == checksum
            and copied.row_count == cache_entry.row_count
        ):
            outcome.reused.append(int(definition.cohort_id))
            continue
        to_copy.append((int(definition.cohort_id), checksum, cache_entry.row_count))

    if not to_copy:
        return outcome

    logger.info("Copying %d cohort(s) from cache to %s.%s", len(to_copy), output_schema, output_table)
    mapping = _mapping_relation(
        [
            {"cohort_definition_id": cohort_id, "cohort_checksum": checksum}
            for cohort_id, checksum, _ in to_copy
        ]
    )
    cached = read_table(backend, table_name=cache.table_name, schema=cache.schema)
    relation = mapping.join(cached, mapping.cohort_checksum == cached.cohort_checksum).select(
        cohort_definition_id=mapping.cohort_definition_id,
        subject_id=cached.subject_id,
        cohort_start_date=cached.cohort_start_date,
        cohort_end_date=cached.cohort_end_date,
    )
    ids = [cohort_id for cohort_id, _, _ in to_copy]
    try:
        delete_rows_in(
            backend,
            table_name=output_table,
            schema=output_schema,
            column="cohort_definition_id",
            values=ids,
        )
        insert_relation(
            relation,
            backend=backend,
            target_table=output_table,
            target_schema=output_schema,
        )
        output_map.mark_complete(to_copy)
        outcome.generated.extend(ids)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Cache-to-output copy failed for %d cohort(s)", len(ids))
        outcome.failed.extend(
            {"family": f"cohort-{cohort_id}", "error": f"{type(exc).__name__}: {exc}"} for cohort_id in ids
        )
    logger.info("Copied %d cohort(s) to %s.%s", len(ids), output_schema, output_table)
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
