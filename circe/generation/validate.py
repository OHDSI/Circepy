from __future__ import annotations

from .config import GenerationConfig
from .metadata import GeneratedCohortCounts, ValidationResult
from .tables import COHORT_RESULT_SCHEMA, table_exists


def _cohort_rows(backend, *, cohort_id: int, config: GenerationConfig):
    if not table_exists(backend, config.cohort_table, config.results_schema):
        return None
    relation = backend.table(config.cohort_table, database=config.results_schema)
    if "cohort_definition_id" not in relation.columns:
        return None
    return relation.filter(relation.cohort_definition_id == int(cohort_id))


def get_generated_cohort_counts(
    backend,
    *,
    cohort_id: int,
    config: GenerationConfig,
) -> GeneratedCohortCounts:
    rows = _cohort_rows(backend, cohort_id=cohort_id, config=config)
    if rows is None:
        return GeneratedCohortCounts(
            cohort_id=int(cohort_id),
            row_count=0,
            distinct_subject_count=0,
            min_start_date=None,
            max_end_date=None,
        )

    metrics = rows.aggregate(
        row_count=rows.count(),
        distinct_subject_count=rows.subject_id.nunique(),
        min_start_date=rows.cohort_start_date.min(),
        max_end_date=rows.cohort_end_date.max(),
    ).execute()
    record = metrics.iloc[0]
    return GeneratedCohortCounts(
        cohort_id=int(cohort_id),
        row_count=int(record["row_count"]),
        distinct_subject_count=int(record["distinct_subject_count"]),
        min_start_date=(
            None
            if record["min_start_date"] is None
            else str(record["min_start_date"])
        ),
        max_end_date=(
            None
            if record["max_end_date"] is None
            else str(record["max_end_date"])
        ),
    )


def validate_generated_cohort(
    backend,
    *,
    cohort_id: int,
    config: GenerationConfig,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not table_exists(backend, config.cohort_table, config.results_schema):
        errors.append(
            f"Cohort table '{config.cohort_table}' was not found in schema '{config.results_schema}'."
        )
        return ValidationResult(
            cohort_id=int(cohort_id),
            is_valid=False,
            row_count=None,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    rows = backend.table(config.cohort_table, database=config.results_schema)
    required = set(COHORT_RESULT_SCHEMA.keys())
    missing = required.difference(rows.columns)
    if missing:
        errors.append(
            "Cohort table is missing required columns: " + ", ".join(sorted(missing))
        )
        return ValidationResult(
            cohort_id=int(cohort_id),
            is_valid=False,
            row_count=None,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    scoped = rows.filter(rows.cohort_definition_id == int(cohort_id))
    row_count = int(scoped.count().execute())

    if row_count == 0:
        warnings.append(f"No rows found for cohort_definition_id={cohort_id}.")

    null_subjects = int(scoped.filter(scoped.subject_id.isnull()).count().execute())
    if null_subjects:
        errors.append(f"Found {null_subjects} rows with null subject_id.")

    null_start = int(scoped.filter(scoped.cohort_start_date.isnull()).count().execute())
    if null_start:
        errors.append(f"Found {null_start} rows with null cohort_start_date.")

    null_end = int(scoped.filter(scoped.cohort_end_date.isnull()).count().execute())
    if null_end:
        errors.append(f"Found {null_end} rows with null cohort_end_date.")

    invalid_windows = int(
        scoped.filter(scoped.cohort_end_date < scoped.cohort_start_date).count().execute()
    )
    if invalid_windows:
        errors.append(
            f"Found {invalid_windows} rows where cohort_end_date is before cohort_start_date."
        )

    return ValidationResult(
        cohort_id=int(cohort_id),
        is_valid=not errors,
        row_count=row_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
