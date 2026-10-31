"""Family-aware cohort-generation sharding.

Cohorts can carry an optional ``family`` tag.  A family is kept together on one
worker so related definitions retain shared execution behavior, while families
are balanced across a configurable number of processes.  All shards write to
the same target cohort table but use independent registry tables.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..cohort_definition_set import CohortDefinitionSet
from ..execution.ibis.operations import create_table, table_exists
from ..execution.ibis_compat import literal_rows_relation
from ..execution.session import SESSION_TABLE
from .backend import close_backend, connect_backend
from .cache import CohortCache, copy_cache_to_output, ensure_output_table
from .payload import RunnerPayload
from .runner import (
    RunnerError,
    _load_definitions,
    run_cache_shard,
)

logger = logging.getLogger(__name__)

_TARGET_SCHEMA = {
    "cohort_definition_id": "int64",
    "subject_id": "int64",
    "cohort_start_date": "date",
    "cohort_end_date": "date",
}
_SESSION_SCHEMA = {
    "session_prefix": "string",
    "created_at": "timestamp",
}

__all__ = [
    "CohortShard",
    "ShardedResult",
    "ShardingError",
    "build_shard_payload",
    "ensure_target_table",
    "plan_family_shards",
    "plan_payload_shards",
    "run_sharded_cohort_generation",
    "shard_manifest",
    "write_shard_manifest",
]


class ShardingError(RuntimeError):
    """Raised when one or more shards fail."""

    def __init__(self, message: str, *, errors: dict[int, str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or {}


@dataclass(frozen=True)
class CohortShard:
    """One worker's assigned families and cohort ids."""

    shard_id: int
    families: tuple[str, ...]
    cohort_ids: tuple[int, ...]
    registry_table: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "shard_id": self.shard_id,
            "families": list(self.families),
            "cohort_ids": list(self.cohort_ids),
            "registry_table": self.registry_table,
        }


@dataclass
class ShardedResult:
    """Aggregated result of a sharded generation run."""

    shards: list[CohortShard]
    results: dict[int, dict[str, Any]]
    failures: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        failures = list(self.failures)
        return {
            "status": "PARTIAL" if failures else "COMPLETE",
            "shard_count": len(self.shards),
            "shards": [shard.to_dict() for shard in self.shards],
            "results": {str(shard_id): result for shard_id, result in self.results.items()},
            "failures": failures,
        }


def plan_family_shards(
    cohort_set: CohortDefinitionSet,
    *,
    shard_count: int = 10,
    registry_table: str | None = "cohort_definition_registry",
) -> list[CohortShard]:
    """Balance families across at most *shard_count* workers.

    Families are never split.  Family sizes are balanced with a deterministic
    longest-processing-time assignment by cohort count.
    """
    if shard_count < 1:
        raise ValueError("shard_count must be at least 1")

    grouped: dict[str, list[int]] = {}
    family_labels: dict[str, str | None] = {}
    for cohort in cohort_set:
        tag = (cohort.family or "").strip() or None
        key = tag if tag is not None else f"__cohort_{cohort.cohort_id}"
        grouped.setdefault(key, []).append(cohort.cohort_id)
        family_labels.setdefault(key, tag)

    if not grouped:
        return []

    actual_shard_count = min(shard_count, len(grouped))
    loads = [0] * actual_shard_count
    assignments: list[list[str]] = [[] for _ in range(actual_shard_count)]
    ids_per_shard: list[list[int]] = [[] for _ in range(actual_shard_count)]

    ordered = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    for key, cohort_ids in ordered:
        target = min(range(actual_shard_count), key=lambda index: (loads[index], index))
        assignments[target].append(key)
        ids_per_shard[target].extend(cohort_ids)
        loads[target] += len(cohort_ids)

    shards: list[CohortShard] = []
    for shard_id, (keys, cohort_ids) in enumerate(zip(assignments, ids_per_shard, strict=True)):
        if not cohort_ids:
            continue
        family_tags = tuple(family_labels[key] for key in keys if family_labels[key] is not None)
        shards.append(
            CohortShard(
                shard_id=shard_id,
                families=family_tags,
                cohort_ids=tuple(cohort_ids),
                registry_table=registry_table,
            )
        )
    return shards


def plan_payload_shards(
    payload: RunnerPayload,
    *,
    shard_count: int = 10,
) -> list[CohortShard]:
    """Load a payload's definitions and produce a family-balanced shard plan."""
    cohort_set = _load_definitions(payload)
    if not len(cohort_set):
        raise RunnerError("The cohort definition set is empty; nothing to shard.")
    return plan_family_shards(
        cohort_set,
        shard_count=shard_count,
        registry_table=payload.target.registry_table,
    )


def build_shard_payload(payload: RunnerPayload, shard: CohortShard) -> RunnerPayload:
    """Create a worker payload that loads exactly one shard's cohort ids."""
    definitions = payload.definitions.model_copy(
        update={"families": None, "cohort_ids": list(shard.cohort_ids)}
    )
    target = payload.target
    metadata = {
        **payload.metadata,
        "circe_shard": shard.shard_id,
        "circe_families": list(shard.families),
    }
    return payload.model_copy(update={"definitions": definitions, "target": target, "metadata": metadata})


def ensure_target_table(payload: RunnerPayload) -> None:
    """Create the shared target cohort table before workers start.

    Parallel workers must not race to create the same table.  The table is
    created empty with the OHDSI cohort-table columns if it does not exist.
    """
    target = payload.target
    if target.schema_name == payload.cdm_schema:
        warnings.warn(
            "The shard target schema is the CDM schema. Cohort, session and registry "
            "tables must be written to a scratch/results schema, not the CDM.",
            UserWarning,
            stacklevel=2,
        )

    backend = connect_backend(payload.backend)
    try:
        if not table_exists(backend, table_name=target.table, schema=target.schema_name):
            empty = literal_rows_relation([], schema=_TARGET_SCHEMA)
            try:
                create_table(
                    backend,
                    table_name=target.table,
                    schema=target.schema_name,
                    obj=empty,
                    overwrite=False,
                )
            except Exception:
                # Another coordinator may have created it between the check and create.
                if not table_exists(backend, table_name=target.table, schema=target.schema_name):
                    raise

        # Pre-create the session registry too. Otherwise the first workers race
        # to create it and log DuplicateTable errors (generation still works, but
        # the run is noisy and session registration may be skipped).
        if not table_exists(backend, table_name=SESSION_TABLE, schema=target.schema_name):
            empty_session = literal_rows_relation([], schema=_SESSION_SCHEMA)
            try:
                create_table(
                    backend,
                    table_name=SESSION_TABLE,
                    schema=target.schema_name,
                    obj=empty_session,
                    overwrite=False,
                )
            except Exception:
                if not table_exists(backend, table_name=SESSION_TABLE, schema=target.schema_name):
                    raise
    finally:
        close_backend(backend)


def _run_shard_worker(payload: dict[str, Any], retries: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return run_cache_shard(RunnerPayload.model_validate(payload))
        except Exception as exc:  # noqa: BLE001 - worker boundary retries all failures
            last_error = exc
            if attempt >= retries:
                break
            delay = min(2**attempt, 30)
            logger.warning(
                "Shard %s failed (attempt %d/%d); retrying in %ss: %s",
                payload.get("metadata", {}).get("circe_shard"),
                attempt + 1,
                retries + 1,
                delay,
                exc,
            )
            time.sleep(delay)
    assert last_error is not None
    raise last_error


def ensure_output_table_for_payload(payload: RunnerPayload) -> None:
    target = payload.target
    backend = connect_backend(payload.backend)
    try:
        ensure_output_table(backend, schema=target.schema_name, table=target.table)
    finally:
        close_backend(backend)


def _ensure_cache_for_payload(payload: RunnerPayload) -> None:
    target = payload.target
    backend = connect_backend(payload.backend)
    try:
        CohortCache(
            backend,
            schema=target.cache_schema or target.schema_name,
            table_name=target.cache_table,
            registry_table=target.registry_table or "cohort_cache_registry",
        )
    finally:
        close_backend(backend)


def run_sharded_cohort_generation(
    payload: RunnerPayload,
    *,
    shard_count: int = 10,
    max_workers: int = 10,
    retries: int = 2,
) -> ShardedResult:
    """Build family-balanced cache shards, then copy all cached results.

    Workers only populate the checksum-keyed cache.  The integer-id output table
    is written by the coordinator after all workers finish.  Failures are
    collected per shard/family; successful cached cohorts are still copied.
    """
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")
    if retries < 0:
        raise ValueError("retries must be non-negative")

    shards = plan_payload_shards(payload, shard_count=shard_count)
    if not shards:
        raise RunnerError("The shard plan is empty; no workers to start.")

    target = payload.target
    cache_schema = target.cache_schema or target.schema_name
    registry_table = target.registry_table or "cohort_cache_registry"
    ensure_target_table(payload)
    _ensure_cache_for_payload(payload)

    worker_payloads = {
        shard.shard_id: build_shard_payload(payload, shard).model_dump(mode="json", by_alias=True)
        for shard in shards
    }
    results: dict[int, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    workers = min(max_workers, len(shards))
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_run_shard_worker, worker_payloads[shard.shard_id], retries): shard
            for shard in shards
        }
        for future in as_completed(futures):
            shard = futures[future]
            try:
                shard_result = future.result()
                results[shard.shard_id] = shard_result
                failures.extend(shard_result.get("failed", []))
            except Exception as exc:  # noqa: BLE001 - isolate shard failures
                logger.exception("Shard %d failed", shard.shard_id)
                failures.append(
                    {
                        "family": f"shard-{shard.shard_id}",
                        "error": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                    }
                )

    backend = connect_backend(payload.backend)
    try:
        cache = CohortCache(
            backend,
            schema=cache_schema,
            table_name=target.cache_table,
            registry_table=registry_table,
        )
        definitions = list(_load_definitions(payload))
        copy_result = copy_cache_to_output(
            backend,
            cache,
            definitions,
            output_schema=target.schema_name,
            output_table=target.table,
        )
        failures.extend(copy_result.failed)
    finally:
        close_backend(backend)

    return ShardedResult(shards=shards, results=results, failures=failures)


def shard_manifest(payload: RunnerPayload, shard_count: int = 10) -> dict[str, Any]:
    """Return a JSON-serializable plan for external orchestrators."""
    shards = plan_payload_shards(payload, shard_count=shard_count)
    return {
        "shard_count": len(shards),
        "target": payload.target.model_dump(mode="json", by_alias=True),
        "shards": [
            {
                **shard.to_dict(),
                "payload": build_shard_payload(payload, shard).model_dump(mode="json", by_alias=True),
            }
            for shard in shards
        ],
    }


def write_shard_manifest(
    payload: RunnerPayload,
    path: str | Path,
    *,
    shard_count: int = 10,
) -> Path:
    """Write a shard manifest for Databricks Workflows/Prefect fan-out."""
    destination = Path(path)
    destination.write_text(
        json.dumps(shard_manifest(payload, shard_count=shard_count), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination
