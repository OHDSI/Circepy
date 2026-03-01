from __future__ import annotations

from .config import GenerationConfig
from .metadata import GenerationStatus
from .tables import cohort_row_count, read_rows


def _by_cohort_id(rows: list[dict], cohort_id: int) -> dict | None:
    for row in rows:
        try:
            if int(row.get("cohort_id")) == int(cohort_id):
                return row
        except (TypeError, ValueError):
            continue
    return None


def get_generated_cohort_status(
    backend,
    *,
    cohort_id: int,
    config: GenerationConfig,
) -> GenerationStatus:
    metadata_rows = read_rows(backend, config.metadata_table, config.results_schema)
    checksum_rows = read_rows(backend, config.checksum_table, config.results_schema)

    metadata_row = _by_cohort_id(metadata_rows, cohort_id)
    checksum_row = _by_cohort_id(checksum_rows, cohort_id)

    if metadata_row is None and checksum_row is None:
        return GenerationStatus(
            cohort_id=int(cohort_id),
            cohort_name=None,
            policy=None,
            status="missing",
            target_table=config.cohort_table,
            results_schema=config.results_schema,
            row_count=cohort_row_count(backend, config=config, cohort_id=cohort_id),
            expression_hash=None,
            options_hash=None,
            combined_hash=None,
            previous_combined_hash=None,
            generated_at=None,
            message="No generation metadata/checksum records found.",
        )

    return GenerationStatus(
        cohort_id=int(cohort_id),
        cohort_name=None if metadata_row is None else metadata_row.get("cohort_name"),
        policy=None,
        status=(
            "unknown"
            if metadata_row is None
            else str(metadata_row.get("status") or "unknown")
        ),
        target_table=(
            config.cohort_table
            if metadata_row is None
            else str(metadata_row.get("target_table") or config.cohort_table)
        ),
        results_schema=(
            config.results_schema
            if metadata_row is None
            else str(metadata_row.get("results_schema") or config.results_schema)
        ),
        row_count=cohort_row_count(backend, config=config, cohort_id=cohort_id),
        expression_hash=(
            None if metadata_row is None else metadata_row.get("expression_hash")
        ),
        options_hash=(
            None if checksum_row is None else checksum_row.get("options_hash")
        ),
        combined_hash=(
            None if checksum_row is None else checksum_row.get("combined_hash")
        ),
        previous_combined_hash=(
            None if checksum_row is None else checksum_row.get("combined_hash")
        ),
        generated_at=(
            None
            if metadata_row is None
            else metadata_row.get("generated_at")
        ),
        message=None,
    )
