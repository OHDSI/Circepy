"""Registry abstractions for incremental cohort generation metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol, Union

from .cohort_definition_set import CohortId, SetId


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CohortRunRecord:
    cohort_id: CohortId
    definition_hash: str
    status: str
    target_schema: Optional[str]
    target_table: str
    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    row_count: Optional[int] = None
    definition_version: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class SetRunRecord:
    set_id: SetId
    set_hash: str
    status: str
    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class SetMemberRecord:
    set_id: SetId
    cohort_id: CohortId
    definition_hash: str
    ordinal: int
    recorded_at: datetime


class CohortGenerationRegistry(Protocol):
    """Persistence contract for cohort and set execution metadata."""

    def get_cohort_run(self, cohort_id: CohortId) -> Optional[CohortRunRecord]:
        ...

    def upsert_cohort_run(self, record: CohortRunRecord) -> None:
        ...

    def get_set_run(self, set_id: SetId) -> Optional[SetRunRecord]:
        ...

    def upsert_set_run(self, record: SetRunRecord) -> None:
        ...

    def get_set_members(self, set_id: SetId) -> List[SetMemberRecord]:
        ...

    def replace_set_members(self, set_id: SetId, members: List[SetMemberRecord]) -> None:
        ...


class InMemoryRegistry:
    """Default registry implementation backed by process memory."""

    def __init__(self) -> None:
        self._cohort_runs: Dict[Union[str, int], CohortRunRecord] = {}
        self._set_runs: Dict[Union[str, int], SetRunRecord] = {}
        self._set_members: Dict[Union[str, int], List[SetMemberRecord]] = {}

    def get_cohort_run(self, cohort_id: CohortId) -> Optional[CohortRunRecord]:
        return self._cohort_runs.get(cohort_id)

    def upsert_cohort_run(self, record: CohortRunRecord) -> None:
        self._cohort_runs[record.cohort_id] = record

    def get_set_run(self, set_id: SetId) -> Optional[SetRunRecord]:
        return self._set_runs.get(set_id)

    def upsert_set_run(self, record: SetRunRecord) -> None:
        self._set_runs[record.set_id] = record

    def get_set_members(self, set_id: SetId) -> List[SetMemberRecord]:
        return list(self._set_members.get(set_id, []))

    def replace_set_members(self, set_id: SetId, members: List[SetMemberRecord]) -> None:
        self._set_members[set_id] = list(members)

