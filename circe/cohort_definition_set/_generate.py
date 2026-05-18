"""Batch cohort generation for CohortDefinitionSet."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from ..execution.api import build_cohort, write_cohort
from ..execution.ibis.codesets import _CODESET_TABLE, build_batch_codeset_table, drop_codeset_table
from ..execution.ibis.context import make_execution_context
from ..execution.normalize.cohort import normalize_cohort
from ._checksum_store import load_checksums, upsert_generation_history
from ._core import CohortDefinition, CohortDefinitionSet, CohortGenerationResult

if TYPE_CHECKING:
    from ..execution.typing import IbisBackendLike, Table

logger = logging.getLogger(__name__)

_backend_lock = threading.Lock()


def _collect_concept_sets(
    cohort_definition_set: CohortDefinitionSet,
) -> dict[int: NormalizedConceptSet]:  # type: ignore
    """Normalize all cohort expressions and merge concept sets."""
    from ..execution.normalize.cohort import NormalizedConceptSet  # noqa: F401

    all_sets: dict[int, NormalizedConceptSet] = {}
    for cohort in cohort_definition_set:
        normalized = normalize_cohort(cohort.expression)
        for cid, cset in normalized.concept_sets.items():
            if cid not in all_sets:
                all_sets[cid] = cset
    return all_sets


def _build_and_return_batch_codesets(
    *,
    backend: IbisBackendLike,
    concept_sets: dict,
    results_schema: str | None,
    vocabulary_schema: str | None,
    results_table_name: str,
) -> Table:
    """Build batch codeset table. Called inside a thread."""
    from ..execution.typing import Table as TableType

    return build_batch_codeset_table(
        backend=backend,
        concept_sets=concept_sets,
        batch_table_name=results_table_name,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        use_persistent_cache=False,
        temporary=False,
    )


def _process_single_cohort(
    cohort: CohortDefinition,
    *,
    backend: IbisBackendLike,
    cdm_schema: str | None,
    results_schema: str | None,
    vocabulary_schema: str | None,
    cohort_table: str,
    codeset_table: Table,
) -> tuple[datetime, datetime]:
    """Build and write a single cohort against a pre-populated codeset table.

    Thread-safe via ``_backend_lock``.

    Returns ``(start_time, end_time)`` of the database-materialization
    phase so the caller can compute execution duration.
    """
    from ..execution.ibis.materialize import project_to_ohdsi_cohort_table

    with _backend_lock:
        start_time = datetime.now()
        new_rows = build_cohort(
            cohort.expression,
            backend=backend,
            cdm_schema=cdm_schema,  # type: ignore[arg-type]
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
            cohort_id=cohort.cohort_id,
            codeset_table=codeset_table,
        )
        projected = project_to_ohdsi_cohort_table(new_rows, cohort_id=cohort.cohort_id)
        write_cohort(
            compiled_relation=projected,
            backend=backend,
            cdm_schema=cdm_schema,  # type: ignore[arg-type]
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
    checksum_table: str = "cohort_checksum",
    stop_on_error: bool = True,
    compile_timeout: float | None = None,
) -> list[CohortGenerationResult]:
    """Generate all cohorts in a CohortDefinitionSet and write them to a shared table.

    This is the async counterpart of :func:`generate_cohort_set`.  It wraps
    the synchronous build/write pipeline in :func:`asyncio.to_thread` so
    that each cohort's work does not block the event loop.  When
    *compile_timeout* is set, cohorts taking longer than the given number
    of seconds are recorded as ``FAILED`` and the next cohort proceeds
    (subject to *stop_on_error*).

    All exception types (not just ``ExecutionError``) are caught and
    recorded as ``FAILED``, ensuring that transient database errors such as
    Databricks ``ServerOperationError`` do not abort the entire batch.

    A single batch codeset table is populated at the start once with *all*
    concept sets from *all* cohorts, so that concept-ancestor and
    concept-relationship lookups happen in one bulk query rather than per
    cohort.  The table is dropped before returning.
    """
    total = len(cohort_definition_set)

    from ..execution.engine.group_operators import _COMPILED_CORRELATED_EVENTS

    _COMPILED_CORRELATED_EVENTS.clear()

    previous_checksums: dict[int, str] = {}
    if incremental:
        previous_checksums = await asyncio.to_thread(
            load_checksums,
            backend,
            schema=results_schema,
            table_name=checksum_table,
        )

    # Collect and materialise concept sets once for the entire batch
    all_concept_sets = await asyncio.to_thread(_collect_concept_sets, cohort_definition_set)
    batch_codesets_table_name = _CODESET_TABLE
    codeset_table: Table | None = None
    if all_concept_sets:
        codeset_table = await asyncio.to_thread(
            _build_and_return_batch_codesets,
            backend=backend,
            concept_sets=all_concept_sets,
            results_schema=results_schema,
            vocabulary_schema=vocabulary_schema,
            results_table_name=batch_codesets_table_name,
        )
    else:
        # No concept sets -- create empty memtable to satisfy ExecutionContext
        import ibis  # noqa: PLC0415
        codeset_table = ibis.memtable(
            {"codeset_id": [], "concept_id": []},
            schema={"codeset_id": "int64", "concept_id": "int64"},
        )

    results: list[CohortGenerationResult] = []

    logger.info(
        "Generating %d cohort(s) (incremental=%s) using batch codeset table",
        total,
        incremental,
    )

    try:
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
                        codeset_table=codeset_table,
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
                    f"Cohort {cohort.cohort_id} ({cohort.cohort_name}) "
                    f"exceeded timeout of {compile_timeout:.0f}s"
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
            for stage in ("primary", "qualified", "included", "ended"):
                with contextlib.suppress(Exception):
                    backend.drop_table(
                        f"__cg_{cohort.cohort_id}_{stage}", database=schema, force=True
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
    finally:
        if all_concept_sets:
            await asyncio.to_thread(
                drop_codeset_table,
                backend,
                batch_table_name=batch_codesets_table_name,
                results_schema=results_schema,
            )


def generate_cohort_set(
    cohort_definition_set: CohortDefinitionSet,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    cohort_table: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    incremental: bool = False,
    checksum_table: str = "cohort_checksum",
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
        dict with counts for each status, e.g.
        ``{"COMPLETE": 2, "SKIPPED": 1, "FAILED": 0}``.
    """
    counts: dict[Literal["COMPLETE", "SKIPPED", "FAILED"], int] = {
        "COMPLETE": 0,
        "SKIPPED": 0,
        "FAILED": 0,
    }
    for r in results:
        counts[r.status] += 1
    return counts
