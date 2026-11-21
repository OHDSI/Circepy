"""Cohort-era construction for era-cache reads.

Given a target cohort (``subject_id``, ``cohort_start_date``,
``cohort_end_date``) and the observation periods around each index date, build
a set of cohort eras per cohort row.

Feature prevalence is then computed by joining cached feature eras to cohort
eras: a feature counts once per cohort row if any of its events falls inside one
of the row's read windows.  This is what lets one cached build answer several
time-at-risk windows and several cohorts without regenerating anything.

Era rules:

- era bounds are ``index + start_days`` and ``index + end_days``;
- the observation period clamps the era when requested;
- optional ``restrict_end_date`` clamps to a study end date;
- eras with ``start > end`` are dropped.

Each era specification produces a distinct ``era_sequence`` so a row's eras do
not overlap *across* specifications by construction (they are separate rows for
separate windows).  Within one specification a row has exactly one era.
"""

from __future__ import annotations

from dataclasses import dataclass

import ibis

from ..execution.typing import IbisBackendLike, Table

__all__ = ["CohortEraSpec", "build_cohort_eras"]


@dataclass(frozen=True)
class CohortEraSpec:
    """Time-at-risk definition, expressed relative to the cohort index date."""

    start_days: int | None
    end_days: int
    restrict_observation_period: bool = True
    restrict_end_date: str | None = None

    def canonical_payload(self) -> dict[str, object]:
        return {
            "start_days": None if self.start_days is None else int(self.start_days),
            "end_days": int(self.end_days),
            "restrict_observation_period": bool(self.restrict_observation_period),
            "restrict_end_date": self.restrict_end_date,
        }


def _read(backend: IbisBackendLike, table_name: str, schema: str | None) -> Table:
    if schema is not None:
        try:
            return backend.table(table_name, database=schema)
        except TypeError:
            pass
    return backend.table(table_name)


def _attach_observation_period(cohort: Table, observation_period: Table) -> Table:
    """Join each cohort row to the observation period covering its index date."""
    op = observation_period.select(
        observation_period.person_id.cast("int64").name("op_person_id"),
        observation_period.observation_period_start_date.cast("date").name("op_start"),
        observation_period.observation_period_end_date.cast("date").name("op_end"),
    )
    joined = cohort.join(op, cohort.subject_id == op.op_person_id)
    ranked = joined.mutate(
        _op_rank=ibis.row_number().over(
            ibis.window(
                group_by=[joined.row_id],
                order_by=[ibis.desc(joined.op_end - joined.op_start), joined.op_start],
            )
        )
    )
    return ranked.filter(ranked._op_rank == 0).select(
        ranked.row_id,
        ranked.subject_id,
        ranked.cohort_start_date,
        ranked.cohort_end_date,
        ranked.op_start,
        ranked.op_end,
    )


def build_cohort_eras(
    cohort: Table,
    *,
    eras: list[CohortEraSpec],
    observation_period: Table | None = None,
) -> Table:
    """Return ``(row_id, subject_id, era_sequence, start_day, end_day)`` per cohort row."""
    if not eras:
        raise ValueError("build_cohort_eras requires at least one era specification.")

    base = cohort.select(
        cohort.row_id.cast("int64").name("row_id"),
        cohort.subject_id.cast("int64").name("subject_id"),
        cohort.cohort_start_date.cast("date").name("cohort_start_date"),
        cohort.cohort_end_date.cast("date").name("cohort_end_date"),
    ).distinct()

    if observation_period is not None:
        rows = _attach_observation_period(base, observation_period)
    else:
        rows = base.mutate(
            op_start=base.cohort_start_date,
            op_end=base.cohort_end_date,
        )

    parts: list[Table] = []
    for index, spec in enumerate(eras):
        # ``start_days=None`` means "unbounded prior history": clamp to the
        # observation-period start when available, otherwise to the index date.
        if spec.start_days is None:
            start = rows.op_start
        else:
            start = rows.cohort_start_date + ibis.interval(days=int(spec.start_days))
        stop = rows.cohort_start_date + ibis.interval(days=int(spec.end_days))
        if spec.restrict_observation_period:
            start = ibis.greatest(start, rows.op_start)
            stop = ibis.least(stop, rows.op_end)
        if spec.restrict_end_date is not None:
            stop = ibis.least(stop, ibis.literal(spec.restrict_end_date).cast("date"))

        segment = rows.select(
            rows.row_id,
            rows.subject_id,
            era_sequence=ibis.literal(index, type="int32"),
            start_day=start,
            end_day=stop,
        )
        parts.append(segment.filter(segment.start_day <= segment.end_day))

    combined = parts[0]
    for part in parts[1:]:
        combined = combined.union(part, distinct=False)
    return combined


def read_observation_period(
    backend: IbisBackendLike,
    *,
    cdm_schema: str,
) -> Table:
    return _read(backend, "observation_period", cdm_schema)
