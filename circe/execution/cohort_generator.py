"""Ibis-first orchestration for incremental cohort generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import uuid
from typing import Any, List, Optional

from .cohort_definition_set import CohortDefinitionMember, CohortDefinitionSet
from .hash_utils import compute_definition_hash, compute_set_hash
from .options import SchemaName, schema_to_str
from .registry import (
    CohortGenerationRegistry,
    CohortRunRecord,
    InMemoryRegistry,
    SetMemberRecord,
    SetRunRecord,
    utc_now,
)


@dataclass
class GenerationResult:
    cohort_id: Any
    definition_hash: str
    status: str
    executed: bool
    skipped: bool
    run_id: str
    target_table: str
    target_schema: Optional[str]
    row_count: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class SetGenerationResult:
    set_id: Any
    set_hash: str
    status: str
    run_id: str
    cohort_results: List[GenerationResult]
    removed_cohort_ids: List[Any]
    error_message: Optional[str] = None


class CohortGenerator:
    """Incremental cohort writer with hash-based replacement semantics."""

    def __init__(
        self,
        executor: Any,
        registry: Optional[CohortGenerationRegistry] = None,
        running_timeout_seconds: int = 3600,
    ) -> None:
        self._executor = executor
        self._registry = registry or InMemoryRegistry()
        self._running_timeout = timedelta(seconds=running_timeout_seconds)

    def compute_definition_hash(self, expression: Any) -> str:
        return compute_definition_hash(expression)

    def needs_execution(self, cohort_id: Any, definition_hash: str) -> bool:
        prior = self._registry.get_cohort_run(cohort_id)
        if prior is None:
            return True
        if prior.status == "success" and prior.definition_hash == definition_hash:
            return False
        return True

    def record_run_start(
        self,
        *,
        cohort_id: Any,
        definition_hash: str,
        target_table: str,
        target_schema: Optional[str],
        run_id: str,
        definition_version: Optional[str] = None,
    ) -> None:
        self._registry.upsert_cohort_run(
            CohortRunRecord(
                cohort_id=cohort_id,
                definition_hash=definition_hash,
                definition_version=definition_version,
                target_schema=target_schema,
                target_table=target_table,
                status="running",
                row_count=None,
                started_at=utc_now(),
                finished_at=None,
                run_id=run_id,
                error_message=None,
            )
        )

    def record_run_success(
        self,
        *,
        cohort_id: Any,
        definition_hash: str,
        target_table: str,
        target_schema: Optional[str],
        run_id: str,
        row_count: Optional[int],
        definition_version: Optional[str] = None,
    ) -> None:
        run = self._registry.get_cohort_run(cohort_id)
        started_at = run.started_at if run is not None else utc_now()
        self._registry.upsert_cohort_run(
            CohortRunRecord(
                cohort_id=cohort_id,
                definition_hash=definition_hash,
                definition_version=definition_version,
                target_schema=target_schema,
                target_table=target_table,
                status="success",
                row_count=row_count,
                started_at=started_at,
                finished_at=utc_now(),
                run_id=run_id,
                error_message=None,
            )
        )

    def record_run_failure(
        self,
        *,
        cohort_id: Any,
        definition_hash: str,
        target_table: str,
        target_schema: Optional[str],
        run_id: str,
        error_message: str,
        definition_version: Optional[str] = None,
    ) -> None:
        run = self._registry.get_cohort_run(cohort_id)
        started_at = run.started_at if run is not None else utc_now()
        self._registry.upsert_cohort_run(
            CohortRunRecord(
                cohort_id=cohort_id,
                definition_hash=definition_hash,
                definition_version=definition_version,
                target_schema=target_schema,
                target_table=target_table,
                status="failed",
                row_count=None,
                started_at=started_at,
                finished_at=utc_now(),
                run_id=run_id,
                error_message=error_message,
            )
        )

    def generate(
        self,
        expression: Any,
        cohort_id: Any,
        table: str,
        schema: Optional[SchemaName] = None,
        incremental: bool = True,
        overwrite_on_hash_change: bool = True,
        definition_version: Optional[str] = None,
    ) -> GenerationResult:
        definition_hash = self.compute_definition_hash(expression)
        target_schema = schema_to_str(schema) or schema_to_str(
            self._executor.options.result_schema
        )
        prior = self._registry.get_cohort_run(cohort_id)

        if (
            prior
            and prior.status == "running"
            and prior.started_at + self._running_timeout > utc_now()
        ):
            raise RuntimeError(
                f"Cohort {cohort_id} already has a running execution (run_id={prior.run_id})."
            )

        if incremental and not self.needs_execution(cohort_id, definition_hash):
            return GenerationResult(
                cohort_id=cohort_id,
                definition_hash=definition_hash,
                status="skipped",
                executed=False,
                skipped=True,
                run_id=prior.run_id if prior else "",
                target_table=table,
                target_schema=target_schema,
                row_count=prior.row_count if prior else None,
            )

        run_id = str(uuid.uuid4())
        self.record_run_start(
            cohort_id=cohort_id,
            definition_hash=definition_hash,
            target_table=table,
            target_schema=target_schema,
            run_id=run_id,
            definition_version=definition_version,
        )

        try:
            hash_changed = prior is not None and prior.definition_hash != definition_hash
            # First run uses overwrite to guarantee table creation for backends
            # that do not support append-into-missing-table behavior.
            overwrite = prior is None or bool(hash_changed and overwrite_on_hash_change)
            append = not overwrite
            written = self._executor.write(
                expression,
                table=table,
                schema=schema,
                overwrite=overwrite,
                append=append,
                cohort_id=cohort_id,
            )
            row_count = _extract_row_count(written)
            self.record_run_success(
                cohort_id=cohort_id,
                definition_hash=definition_hash,
                target_table=table,
                target_schema=target_schema,
                run_id=run_id,
                row_count=row_count,
                definition_version=definition_version,
            )
            return GenerationResult(
                cohort_id=cohort_id,
                definition_hash=definition_hash,
                status="success",
                executed=True,
                skipped=False,
                run_id=run_id,
                target_table=table,
                target_schema=target_schema,
                row_count=row_count,
            )
        except Exception as exc:
            self.record_run_failure(
                cohort_id=cohort_id,
                definition_hash=definition_hash,
                target_table=table,
                target_schema=target_schema,
                run_id=run_id,
                definition_version=definition_version,
                error_message=str(exc),
            )
            return GenerationResult(
                cohort_id=cohort_id,
                definition_hash=definition_hash,
                status="failed",
                executed=True,
                skipped=False,
                run_id=run_id,
                target_table=table,
                target_schema=target_schema,
                error_message=str(exc),
            )

    def compute_set_hash(self, definition_set: CohortDefinitionSet) -> str:
        return compute_set_hash(definition_set)

    def needs_set_execution(self, set_id: Any, set_hash: str) -> bool:
        prior = self._registry.get_set_run(set_id)
        if prior is None:
            return True
        if prior.status == "success" and prior.set_hash == set_hash:
            return False
        return True

    def generate_set(
        self,
        definition_set: CohortDefinitionSet,
        table: str,
        schema: Optional[SchemaName] = None,
        incremental: bool = True,
        remove_missing: bool = False,
        short_circuit_on_unchanged_set: bool = False,
    ) -> SetGenerationResult:
        set_hash = self.compute_set_hash(definition_set)
        run_id = str(uuid.uuid4())
        set_started_at = utc_now()
        prior_members = {
            member.cohort_id: member
            for member in self._registry.get_set_members(definition_set.set_id)
        }

        if (
            short_circuit_on_unchanged_set
            and incremental
            and not self.needs_set_execution(definition_set.set_id, set_hash)
        ):
            return SetGenerationResult(
                set_id=definition_set.set_id,
                set_hash=set_hash,
                status="skipped",
                run_id=run_id,
                cohort_results=[],
                removed_cohort_ids=[],
            )

        self._registry.upsert_set_run(
            SetRunRecord(
                set_id=definition_set.set_id,
                set_hash=set_hash,
                status="running",
                run_id=run_id,
                started_at=set_started_at,
                finished_at=None,
                error_message=None,
            )
        )

        results: List[GenerationResult] = []
        current_ids = set()

        try:
            for member in definition_set.cohorts:
                current_ids.add(member.cohort_id)
                results.append(
                    self.generate(
                        expression=member.expression,
                        cohort_id=member.cohort_id,
                        table=table,
                        schema=schema,
                        incremental=incremental,
                        overwrite_on_hash_change=True,
                    )
                )

            removed_ids: List[Any] = []
            if remove_missing:
                removed_ids = [
                    cohort_id for cohort_id in prior_members if cohort_id not in current_ids
                ]

            member_records = _build_member_snapshot(definition_set)
            self._registry.replace_set_members(definition_set.set_id, member_records)
            self._registry.upsert_set_run(
                SetRunRecord(
                    set_id=definition_set.set_id,
                    set_hash=set_hash,
                    status="success",
                    run_id=run_id,
                    started_at=set_started_at,
                    finished_at=utc_now(),
                    error_message=None,
                )
            )
            return SetGenerationResult(
                set_id=definition_set.set_id,
                set_hash=set_hash,
                status="success",
                run_id=run_id,
                cohort_results=results,
                removed_cohort_ids=removed_ids,
            )
        except Exception as exc:
            self._registry.upsert_set_run(
                SetRunRecord(
                    set_id=definition_set.set_id,
                    set_hash=set_hash,
                    status="failed",
                    run_id=run_id,
                    started_at=set_started_at,
                    finished_at=utc_now(),
                    error_message=str(exc),
                )
            )
            return SetGenerationResult(
                set_id=definition_set.set_id,
                set_hash=set_hash,
                status="failed",
                run_id=run_id,
                cohort_results=results,
                removed_cohort_ids=[],
                error_message=str(exc),
            )

    def generate_many(
        self,
        items: List[CohortDefinitionMember],
        table: str,
        schema: Optional[SchemaName] = None,
        incremental: bool = True,
    ) -> List[GenerationResult]:
        return [
            self.generate(
                expression=item.expression,
                cohort_id=item.cohort_id,
                table=table,
                schema=schema,
                incremental=incremental,
            )
            for item in items
        ]


def _build_member_snapshot(definition_set: CohortDefinitionSet) -> List[SetMemberRecord]:
    now = utc_now()
    return [
        SetMemberRecord(
            set_id=definition_set.set_id,
            cohort_id=member.cohort_id,
            definition_hash=compute_definition_hash(member.expression),
            ordinal=index,
            recorded_at=now,
        )
        for index, member in enumerate(definition_set.cohorts)
    ]


def _extract_row_count(written: Any) -> Optional[int]:
    if written is None:
        return None
    try:
        if hasattr(written, "count"):
            count_expr = written.count()
            if hasattr(count_expr, "execute"):
                count_value = count_expr.execute()
                return int(count_value)
    except Exception:
        return None
    return None

