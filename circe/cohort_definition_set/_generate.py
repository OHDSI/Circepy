"""Batch cohort generation for CohortDefinitionSet."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from ..execution.api import build_cohort, write_cohort
from ..execution.ibis.materialize import project_to_ohdsi_cohort_table
from ._checksum_store import load_checksums, upsert_generation_history
from ._core import CohortDefinition, CohortDefinitionSet, CohortGenerationResult

if TYPE_CHECKING:
    from ..execution.typing import IbisBackendLike

logger = logging.getLogger(__name__)

_backend_lock = threading.Lock()


def _process_single_cohort(
    cohort: CohortDefinition,
    *,
    backend: IbisBackendLike,
    cdm_schema: str | None,
    results_schema: str | None,
    vocabulary_schema: str | None,
    cohort_table: str,
    use_persistent_cache: bool,
) -> tuple[datetime, datetime]:
    """Build and write a single cohort. Thread-safe via ``_backend_lock``.

    Each cohort uses its own per-cohort codeset table built from the
    codeset cache (named from *cohort_table*) when *use_persistent_cache*
    is True, allowing checksum-keyed concept set reuse.

    Returns ``(start_time, end_time)`` of the database-materialization
    phase so the caller can compute execution duration.
    """
    with _backend_lock:
        start_time = datetime.now()
        new_rows = build_cohort(
            cohort.expression,
            backend=backend,
            cdm_schema=cdm_schema,
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
            use_persistent_cache=use_persistent_cache,
            cohort_id=cohort.cohort_id,
            cohort_table=cohort_table,
        )
        projected = project_to_ohdsi_cohort_table(new_rows, cohort_id=cohort.cohort_id)
        write_cohort(
            compiled_relation=projected,
            backend=backend,
            cdm_schema=cdm_schema,
            cohort_table=cohort_table,
            cohort_id=cohort.cohort_id,
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
            if_exists="replace",
        )
        end_time = datetime.now()
        return start_time, end_time


async def async_generate_cohort_set(
    cohort_definition_set: CohortDefinitionSet,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    cohort_table: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    incremental: bool = False,
    checksum_table: str | None = None,
    stop_on_error: bool = True,
    compile_timeout: float | None = None,
) -> list[CohortGenerationResult]:
    """Generate all cohorts in a CohortDefinitionSet and write them to a shared table.

    Each cohort builds its own per-cohort codeset table.  When *incremental*
    is True, concept sets are stored in the persistent
    ``_circe_codeset_cache`` keyed by SHA-256 checksum so that identical
    concept set definitions across cohorts are resolved only once per
    batch.

    All exception types are caught and recorded as ``FAILED``.

    Args:
        cohort_definition_set: The set of cohort definitions to generate.
        backend: Ibis backend connection pointing at the target database.
        cdm_schema: Schema containing the OMOP CDM source tables.
        cohort_table: Name of the OHDSI cohort table to write results into.
        results_schema: Optional schema for both the cohort table and
            checksum table.
        vocabulary_schema: Optional schema for vocabulary tables.
        incremental: If True, skip cohorts whose expression checksum is
            unchanged since the last successful generation.
        checksum_table: Name of the table used to persist generation
            history for incremental runs.
        stop_on_error: If True, raise on the first failure.
        compile_timeout: Maximum seconds per-cohort before timeout.

    Returns:
        A list of :class:`CohortGenerationResult`.
    """
    total = len(cohort_definition_set)

    from ..execution.engine.group_operators import _COMPILED_CORRELATED_EVENTS

    _COMPILED_CORRELATED_EVENTS.clear()

    if checksum_table is None:
        checksum_table = f"{cohort_table}_checksum"

    previous_checksums: dict[int, str] = {}
    if incremental:
        previous_checksums = await asyncio.to_thread(
            load_checksums,
            backend,
            schema=results_schema,
            table_name=checksum_table,
        )

    results: list[CohortGenerationResult] = []

    logger.info("Generating %d cohort(s) (incremental=%s)", total, incremental)

    for i, cohort in enumerate(cohort_definition_set, start=1):
        current_checksum = cohort.expression.checksum()

        if incremental and previous_checksums.get(cohort.cohort_id) == current_checksum:
            logger.info(
                "[%d/%d] Skipping cohort %d (%s) -- checksum unchanged",
                i,
                total,
                cohort.cohort_id,
                cohort.cohort_name,
            )
            results.append(
                CohortGenerationResult(
                    cohort_id=cohort.cohort_id,
                    cohort_name=cohort.cohort_name,
                    status="SKIPPED",
                    checksum=current_checksum,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                )
            )
            continue

        logger.info(
            "[%d/%d] Building cohort %d (%s) ...",
            i,
            total,
            cohort.cohort_id,
            cohort.cohort_name,
        )

        start_time: datetime | None = None
        end_time: datetime | None = None
        try:
            start_time, end_time = await asyncio.wait_for(
                asyncio.to_thread(
                    _process_single_cohort,
                    cohort,
                    backend=backend,
                    cdm_schema=cdm_schema,
                    results_schema=results_schema,
                    vocabulary_schema=vocabulary_schema,
                    cohort_table=cohort_table,
                    use_persistent_cache=incremental,
                ),
                timeout=compile_timeout,
            )

            duration = (end_time - start_time).total_seconds()
            logger.info(
                "[%d/%d] Completed cohort %d (%s) -- duration %.1fs",
                i,
                total,
                cohort.cohort_id,
                cohort.cohort_name,
                duration,
            )
        except asyncio.TimeoutError:
            if end_time is None:
                end_time = datetime.now()
            duration = (end_time - (start_time or end_time)).total_seconds()
            logger.error(
                "[%d/%d] TIMED OUT cohort %d (%s) after %.1fs",
                i,
                total,
                cohort.cohort_id,
                cohort.cohort_name,
                duration,
            )
            timeout_exc = TimeoutError(
                f"Cohort {cohort.cohort_id} ({cohort.cohort_name}) exceeded timeout of {compile_timeout:.0f}s"
            )
            results.append(
                CohortGenerationResult(
                    cohort_id=cohort.cohort_id,
                    cohort_name=cohort.cohort_name,
                    status="FAILED",
                    checksum=current_checksum,
                    start_time=start_time or datetime.now(),
                    end_time=end_time,
                    error=timeout_exc,
                )
            )
            if incremental:
                upsert_generation_history(
                    backend,
                    schema=results_schema,
                    table_name=checksum_table,
                    cohort_id=cohort.cohort_id,
                    checksum=current_checksum,
                    status="FAILED",
                    start_time=start_time or datetime.now(),
                    end_time=end_time,
                )
            if stop_on_error:
                raise timeout_exc from None
            continue
        except Exception as exc:
            if end_time is None:
                end_time = datetime.now()
            duration = (end_time - (start_time or end_time)).total_seconds()
            logger.error(
                "[%d/%d] FAILED cohort %d (%s) after %.1fs: %s",
                i,
                total,
                cohort.cohort_id,
                cohort.cohort_name,
                duration,
                exc,
            )
            results.append(
                CohortGenerationResult(
                    cohort_id=cohort.cohort_id,
                    cohort_name=cohort.cohort_name,
                    status="FAILED",
                    checksum=current_checksum,
                    start_time=start_time or datetime.now(),
                    end_time=end_time,
                    error=exc,
                )
            )
            if incremental:
                upsert_generation_history(
                    backend,
                    schema=results_schema,
                    table_name=checksum_table,
                    cohort_id=cohort.cohort_id,
                    checksum=current_checksum,
                    status="FAILED",
                    start_time=start_time or datetime.now(),
                    end_time=end_time,
                )
            if stop_on_error:
                raise
            continue

        # Clean up staging tables created by the materialized pipeline
        schema = results_schema or cdm_schema
        for stage in ("codesets", "primary", "qualified", "included", "ended"):
            with contextlib.suppress(Exception):
                backend.drop_table(
                    f"__{cohort_table}_{cohort.cohort_id}_{stage}", database=schema, force=True
                )

        results.append(
            CohortGenerationResult(
                cohort_id=cohort.cohort_id,
                cohort_name=cohort.cohort_name,
                status="COMPLETE",
                checksum=current_checksum,
                start_time=start_time or datetime.now(),
                end_time=end_time or datetime.now(),
            )
        )
        if incremental:
            upsert_generation_history(
                backend,
                schema=results_schema,
                table_name=checksum_table,
                cohort_id=cohort.cohort_id,
                checksum=current_checksum,
                status="COMPLETE",
                start_time=start_time or datetime.now(),
                end_time=end_time or datetime.now(),
            )

    summary = summarise_generation_results(results)
    logger.info(
        "Cohort generation complete: %d completed, %d skipped, %d failed",
        summary["COMPLETE"],
        summary["SKIPPED"],
        summary["FAILED"],
    )

    return results


def generate_cohort_set(
    cohort_definition_set: CohortDefinitionSet,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    cohort_table: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    incremental: bool = False,
    checksum_table: str | None = None,
    stop_on_error: bool = True,
) -> list[CohortGenerationResult]:
    """Generate all cohorts in a CohortDefinitionSet and write them to a shared table.

    This synchronous wrapper delegates to :func:`async_generate_cohort_set`
    via :func:`asyncio.run`.  See that function for full parameter
    documentation.

    Raises:
        RuntimeError: If called from within a running asyncio event loop.
            Use :func:`async_generate_cohort_set` directly in that case.
    """
    return asyncio.run(
        async_generate_cohort_set(
            cohort_definition_set,
            backend=backend,
            cdm_schema=cdm_schema,
            cohort_table=cohort_table,
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
            incremental=incremental,
            checksum_table=checksum_table,
            stop_on_error=stop_on_error,
        )
    )


def summarise_generation_results(
    results: list[CohortGenerationResult],
) -> dict[Literal["COMPLETE", "SKIPPED", "FAILED"], int]:
    """Return a count summary of generation results by status.

    Args:
        results: List of CohortGenerationResult from generate_cohort_set.

    Returns:
        dict with counts for each status.
    """
    counts: dict[Literal["COMPLETE", "SKIPPED", "FAILED"], int] = {
        "COMPLETE": 0,
        "SKIPPED": 0,
        "FAILED": 0,
    }
    for r in results:
        counts[r.status] += 1
    return counts
