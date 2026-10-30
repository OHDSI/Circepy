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

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "COMPLETE",
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
        }


def _with_reconnect(backend: Any, action: Callable[[], None]) -> None:
    """Run a registry action, reconnecting once if the connection went stale."""
    try:
        action()
    except Exception:
        reconnect = getattr(backend, "reconnect", None)
        if not callable(reconnect):
            raise
        logger.warning("Registry connection failed; reconnecting and retrying", exc_info=True)
        reconnect()
        action()


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
            if registry is not None:
                _with_reconnect(backend, lambda: registry.mark_incomplete(to_generate))
            subset = CohortDefinitionSet()
            definitions_by_id = {int(definition.cohort_id): definition for definition in to_generate}
            for definition in to_generate:
                subset.add_definition(definition)

            def _mark_complete(result: Any) -> None:
                if registry is None:
                    return
                definition = definitions_by_id[int(result.cohort_id)]
                _with_reconnect(backend, lambda: registry.mark_complete(definition))

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
        close_backend(backend)


__all__ = ["RunnerError", "RunnerResult", "run_cohort_generation"]
