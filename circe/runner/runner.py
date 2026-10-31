"""Execute a cohort-generation payload."""

from __future__ import annotations

import logging
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..cohort_definition_set import (
    CohortDefinitionSet,
    generate_cohort_set,
    load_cohort_definition_set,
)
from .backend import close_backend, connect_backend
from .cache import (
    CohortCache,
    build_cache,
    copy_cache_to_output,
    ensure_output_table,
)
from .payload import RunnerPayload
from .registry import DefinitionRegistry

logger = logging.getLogger(__name__)


class RunnerError(RuntimeError):
    """Raised when cohort generation cannot be completed."""


@dataclass
class RunnerResult:
    """Serializable result of one runner invocation."""

    cdm_schema: str
    target_schema: str
    cohort_table: str
    registry_table: str | None
    loaded: int
    generated: list[int] = field(default_factory=list)
    reused: list[int] = field(default_factory=list)
    generation_results: list[dict[str, Any]] = field(default_factory=list)
    skipped_definitions: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    failures: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "PARTIAL" if self.failures else "COMPLETE",
            "cdm_schema": self.cdm_schema,
            "target_schema": self.target_schema,
            "cohort_table": self.cohort_table,
            "registry_table": self.registry_table,
            "loaded": self.loaded,
            "generated": list(self.generated),
            "reused": list(self.reused),
            "generation_results": list(self.generation_results),
            "skipped_definitions": list(self.skipped_definitions),
            "warnings": list(self.warnings),
            "duration_seconds": round(self.duration_seconds, 3),
            "metadata": dict(self.metadata),
            "failures": list(self.failures),
        }


class _RegistryWriter:
    """Own a short-lived registry connection and retry writes with backoff.

    The registry is written per cohort.  Before each write the backend is
    reconnected so a long-running job cannot hold a stale session; on failure
    the connection is dropped and replaced with a fresh one before retrying.
    """

    def __init__(self, payload: RunnerPayload, target: Any) -> None:
        self._payload = payload
        self._target = target
        self._backend: Any = None
        self._registry: DefinitionRegistry | None = None

    def _connect(self) -> None:
        self.close()
        self._backend = connect_backend(self._payload.backend)
        self._registry = DefinitionRegistry(
            self._backend,
            schema=self._target.schema_name,
            table_name=self._target.registry_table,
            target_table=self._target.table,
        )

    def write(self, action: Callable[[DefinitionRegistry], None], *, attempts: int = 3) -> None:
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                if self._registry is None:
                    self._connect()
                else:
                    reconnect = getattr(self._backend, "reconnect", None)
                    if callable(reconnect):
                        reconnect()
                action(self._registry)
                return
            except Exception as exc:  # noqa: BLE001 - retried, then surfaced
                last_error = exc
                self.close()
                if attempt < attempts - 1:
                    delay = min(2**attempt, 30)
                    logger.warning(
                        "Registry write failed (attempt %d/%d); reconnecting in %ss: %s",
                        attempt + 1,
                        attempts,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
        assert last_error is not None
        raise last_error

    def close(self) -> None:
        if self._backend is not None:
            close_backend(self._backend)
            self._backend = None
            self._registry = None


def _load_definitions(payload: RunnerPayload):
    source = payload.definitions
    return load_cohort_definition_set(
        settings_file=source.settings_file,
        json_folder=source.json_folder,
        sql_folder=source.sql_folder,
        cohort_file_name_format=source.cohort_file_name_format,
        cohort_file_name_value=tuple(source.cohort_file_name_value),
        include_sql=source.include_sql,
        sql_required=source.sql_required,
        unsupported=source.unsupported,
        base_dir=source.base_dir,
        family_column=source.family_column,
        families=source.families,
        cohort_ids=source.cohort_ids,
    )


def run_cohort_generation(payload: RunnerPayload) -> RunnerResult:
    """Load definitions, persist/reuse them, and generate missing cohorts.

    The target cohort table is shared: rows for cohort ids outside this payload
    are never deleted.  When a registry table is configured, reruns skip
    cohorts whose definition checksum and target rows are unchanged.
    """
    started = time.perf_counter()
    loaded = _load_definitions(payload)
    definitions = list(loaded)
    if not definitions:
        raise RunnerError(
            "The cohort definition set is empty; refusing to report a successful run. "
            "Check the mounted Cohorts.csv and unsupported/skipped definitions."
        )
    target = payload.target
    if target.schema_name == payload.cdm_schema:
        warnings.warn(
            "The target schema is the CDM schema. Cohort tables and the definition "
            "registry must be written to a scratch/results schema, not the CDM.",
            UserWarning,
            stacklevel=2,
        )

    backend = connect_backend(payload.backend)
    writer = _RegistryWriter(payload, target) if target.registry_table else None
    try:
        registry: DefinitionRegistry | None = None
        to_generate = definitions
        reused = []
        if target.registry_table:
            registry = DefinitionRegistry(
                backend,
                schema=target.schema_name,
                table_name=target.registry_table,
                target_table=target.table,
            )
            to_generate, reused = registry.plan(
                definitions,
                reuse_existing=target.reuse_existing,
                on_definition_change=target.on_definition_change,
            )

        generated_ids: list[int] = []
        generation_results: list[dict[str, Any]] = []
        if to_generate:
            if writer is not None:
                writer.write(lambda registry: registry.mark_incomplete(to_generate))
            subset = CohortDefinitionSet()
            definitions_by_id = {int(definition.cohort_id): definition for definition in to_generate}
            for definition in to_generate:
                subset.add_definition(definition)

            def _mark_complete(result: Any) -> None:
                if writer is None:
                    return
                definition = definitions_by_id[int(result.cohort_id)]
                writer.write(lambda registry: registry.mark_complete(definition))

            results = generate_cohort_set(
                subset,
                backend=backend,
                cdm_schema=payload.cdm_schema,
                vocabulary_schema=payload.vocabulary_schema,
                results_schema=payload.results_schema,
                cohort_table=target.table,
                shared=payload.shared,
                on_cohort_complete=_mark_complete,
            )
            generated_ids = [result.cohort_id for result in results if result.status == "COMPLETE"]
            generation_results = [
                {
                    "cohort_id": result.cohort_id,
                    "cohort_name": result.cohort_name,
                    "status": result.status,
                    "checksum": result.checksum,
                    "error": str(result.error) if result.error else None,
                }
                for result in results
            ]
            failed = [result for result in results if result.status != "COMPLETE"]
            if failed:
                raise RunnerError(
                    "Cohort generation failed for ids: "
                    + ", ".join(str(result.cohort_id) for result in failed)
                )

        elapsed = time.perf_counter() - started
        logger.info(
            "Generated %d cohort(s), reused %d in %.2fs",
            len(generated_ids),
            len(reused),
            elapsed,
        )
        return RunnerResult(
            cdm_schema=payload.cdm_schema,
            target_schema=target.schema_name,
            cohort_table=target.table,
            registry_table=target.registry_table,
            loaded=len(definitions),
            generated=generated_ids,
            reused=[definition.cohort_id for definition in reused],
            generation_results=generation_results,
            skipped_definitions=[
                {
                    "cohort_id": skipped.cohort_id,
                    "cohort_name": skipped.cohort_name,
                    "reason": skipped.reason,
                }
                for skipped in loaded.report.skipped
            ],
            warnings=list(loaded.report.warnings),
            duration_seconds=elapsed,
            metadata=payload.metadata,
        )
    finally:
        if writer is not None:
            writer.close()
        close_backend(backend)


def run_cache_shard(payload: RunnerPayload) -> dict[str, Any]:
    """Build cache entries for one shard without writing the output table."""
    loaded = _load_definitions(payload)
    definitions = list(loaded)
    if not definitions:
        return {"generated": [], "reused": [], "failed": [], "warnings": []}
    target = payload.target
    cache_schema = target.cache_schema or target.schema_name
    registry_table = target.registry_table or "cohort_cache_registry"
    backend = connect_backend(payload.backend)
    try:
        cache = CohortCache(
            backend,
            schema=cache_schema,
            table_name=target.cache_table,
            registry_table=registry_table,
        )
        outcome = build_cache(
            backend,
            cache,
            definitions,
            cdm_schema=payload.cdm_schema,
            vocabulary_schema=payload.vocabulary_schema,
            shared=payload.shared,
            reuse_existing=target.reuse_existing,
        )
        return {
            "generated": list(outcome.generated),
            "reused": list(outcome.reused),
            "failed": list(outcome.failed),
            "warnings": list(loaded.report.warnings),
        }
    finally:
        close_backend(backend)


def run_cached_cohort_generation(payload: RunnerPayload) -> RunnerResult:
    """Build checksum-keyed cache entries, then copy them to the output table."""
    started = time.perf_counter()
    loaded = _load_definitions(payload)
    definitions = list(loaded)
    if not definitions:
        raise RunnerError(
            "The cohort definition set is empty; refusing to report a successful run. "
            "Check the mounted Cohorts.csv and unsupported/skipped definitions."
        )
    target = payload.target
    if target.schema_name == payload.cdm_schema:
        warnings.warn(
            "The target schema is the CDM schema. Cohort, cache and registry tables "
            "must be written to a scratch/results schema, not the CDM.",
            UserWarning,
            stacklevel=2,
        )

    cache_schema = target.cache_schema or target.schema_name
    registry_table = target.registry_table or "cohort_cache_registry"
    backend = connect_backend(payload.backend)
    try:
        ensure_output_table(backend, schema=target.schema_name, table=target.table)
        cache = CohortCache(
            backend,
            schema=cache_schema,
            table_name=target.cache_table,
            registry_table=registry_table,
        )
        build = build_cache(
            backend,
            cache,
            definitions,
            cdm_schema=payload.cdm_schema,
            vocabulary_schema=payload.vocabulary_schema,
            shared=payload.shared,
            reuse_existing=target.reuse_existing,
        )
        copied = copy_cache_to_output(
            backend,
            cache,
            definitions,
            output_schema=target.schema_name,
            output_table=target.table,
        )
        failures = [*build.failed, *copied.failed]
        elapsed = time.perf_counter() - started
        return RunnerResult(
            cdm_schema=payload.cdm_schema,
            target_schema=target.schema_name,
            cohort_table=target.table,
            registry_table=registry_table,
            loaded=len(definitions),
            generated=list(build.generated),
            reused=list(build.reused),
            generation_results=[],
            skipped_definitions=[
                {
                    "cohort_id": skipped.cohort_id,
                    "cohort_name": skipped.cohort_name,
                    "reason": skipped.reason,
                }
                for skipped in loaded.report.skipped
            ],
            warnings=list(loaded.report.warnings),
            duration_seconds=elapsed,
            metadata=payload.metadata,
            failures=failures,
        )
    finally:
        close_backend(backend)


__all__ = [
    "RunnerError",
    "RunnerResult",
    "run_cache_shard",
    "run_cached_cohort_generation",
    "run_cohort_generation",
]
