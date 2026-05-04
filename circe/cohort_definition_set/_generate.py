"""Batch cohort generation for CohortDefinitionSet."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from ..execution.api import write_cohort
from ..execution.errors import ExecutionError
from ._checksum_store import load_checksums, save_checksums
from ._core import CohortDefinitionSet, CohortGenerationResult

if TYPE_CHECKING:
    from ..execution.typing import IbisBackendLike


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

    This is the Python equivalent of OHDSI/CohortGenerator's ``generateCohortSet()``.
    Each cohort is written to ``cohort_table`` with its ``cohort_id`` stamped into
    ``cohort_definition_id``. If the table already contains rows for a cohort, they
    are replaced (``if_exists="replace"`` semantics from ``write_cohort``).

    When ``incremental=True``, cohorts whose expression checksum matches the stored
    value in ``checksum_table`` are skipped.  Successfully completed cohorts have
    their checksums persisted to ``checksum_table`` so future runs can detect them.

    Args:
        cohort_definition_set: The set of cohort definitions to generate.
        backend: Ibis backend connection pointing at the target database.
        cdm_schema: Schema containing the OMOP CDM source tables.
        cohort_table: Name of the OHDSI cohort table to write results into.
        results_schema: Optional schema for both the cohort table and checksum table.
        vocabulary_schema: Optional schema for vocabulary tables (defaults to cdm_schema).
        incremental: If True, skip cohorts whose expression checksum is unchanged
            since the last successful generation.
        checksum_table: Name of the table used to persist checksums for incremental
            runs.  Defaults to ``"cohort_checksum"``.
        stop_on_error: If True (default), raise the first ExecutionError encountered
            and stop processing remaining cohorts.  If False, record the failure and
            continue.

    Returns:
        A list of :class:`CohortGenerationResult` — one entry per cohort in the
        set, in insertion order.

    Raises:
        ExecutionError: If a cohort fails to generate and ``stop_on_error=True``.

    Example:
        >>> cds = CohortDefinitionSet()
        >>> cds.add(1, "Diabetes", expr1)
        >>> cds.add(2, "Hypertension", expr2)
        >>> results = generate_cohort_set(
        ...     cds,
        ...     backend=conn,
        ...     cdm_schema="main",
        ...     cohort_table="cohort",
        ...     incremental=True,
        ... )
        >>> for r in results:
        ...     print(r.cohort_name, r.status)
    """
    current_checksums = cohort_definition_set.checksums()

    previous_checksums: dict[int, str] = {}
    if incremental:
        previous_checksums = load_checksums(
            backend,
            schema=results_schema,
            table_name=checksum_table,
        )

    results: list[CohortGenerationResult] = []
    completed_this_run: dict[int, tuple[str, datetime]] = {}

    for cohort in cohort_definition_set:
        current_checksum = current_checksums[cohort.cohort_id]

        if incremental and previous_checksums.get(cohort.cohort_id) == current_checksum:
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

        start_time = datetime.now()
        try:
            write_cohort(
                cohort.expression,
                backend=backend,
                cdm_schema=cdm_schema,
                cohort_table=cohort_table,
                cohort_id=cohort.cohort_id,
                results_schema=results_schema,
                vocabulary_schema=vocabulary_schema,
                if_exists="replace",
            )
        except ExecutionError as exc:
            end_time = datetime.now()
            results.append(
                CohortGenerationResult(
                    cohort_id=cohort.cohort_id,
                    cohort_name=cohort.cohort_name,
                    status="FAILED",
                    checksum=current_checksum,
                    start_time=start_time,
                    end_time=end_time,
                    error=exc,
                )
            )
            if stop_on_error:
                raise
            continue

        end_time = datetime.now()
        results.append(
            CohortGenerationResult(
                cohort_id=cohort.cohort_id,
                cohort_name=cohort.cohort_name,
                status="COMPLETE",
                checksum=current_checksum,
                start_time=start_time,
                end_time=end_time,
            )
        )
        completed_this_run[cohort.cohort_id] = (current_checksum, end_time)

    if incremental and completed_this_run:
        save_checksums(
            backend,
            schema=results_schema,
            table_name=checksum_table,
            completed=completed_this_run,
        )

    return results


def summarise_generation_results(
    results: list[CohortGenerationResult],
) -> dict[Literal["COMPLETE", "SKIPPED", "FAILED"], int]:
    """Return a count summary of generation results by status.

    Args:
        results: List of CohortGenerationResult from generate_cohort_set.

    Returns:
        dict with counts for each status, e.g. {"COMPLETE": 2, "SKIPPED": 1, "FAILED": 0}.
    """
    counts: dict[Literal["COMPLETE", "SKIPPED", "FAILED"], int] = {
        "COMPLETE": 0,
        "SKIPPED": 0,
        "FAILED": 0,
    }
    for r in results:
        counts[r.status] += 1
    return counts
