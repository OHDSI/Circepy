from __future__ import annotations

from ..execution._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class GeneratedCohortRecord:
    cohort_id: int
    cohort_name: str | None
    target_table: str
    results_schema: str
    expression_hash: str
    engine_version: str
    generated_at: str
    is_subset: bool
    parent_cohort_id: int | None
    subset_definition_id: str | None
    status: str


@frozen_slots_dataclass
class GeneratedSubsetRecord:
    subset_definition_id: str
    subset_name: str
    parent_cohort_id: int
    operator_sequence_hash: str
    generated_cohort_id: int
    dependency_hash: str
    dependency_payload: str
    generated_at: str


@frozen_slots_dataclass
class GenerationStatus:
    cohort_id: int
    cohort_name: str | None
    policy: str | None
    status: str
    target_table: str
    results_schema: str
    row_count: int | None
    expression_hash: str | None
    options_hash: str | None
    combined_hash: str | None
    previous_combined_hash: str | None
    generated_at: str | None
    message: str | None = None


@frozen_slots_dataclass
class GenerationSetStatus:
    total: int
    generated: int
    replaced: int
    skipped: int
    failed: int
    statuses: tuple[GenerationStatus, ...]


@frozen_slots_dataclass
class GeneratedCohortCounts:
    cohort_id: int
    row_count: int
    distinct_subject_count: int
    min_start_date: str | None
    max_end_date: str | None


@frozen_slots_dataclass
class ValidationResult:
    cohort_id: int
    is_valid: bool
    row_count: int | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
