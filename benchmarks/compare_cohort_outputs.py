#!/usr/bin/env python3
"""Cross-implementation cohort output validator.

Compares the row-level output of two cohort generation implementations
(e.g. R/CohortGenerator vs Python/circe) to verify they produce identical
``(subject_id, cohort_start_date, cohort_end_date)`` rows for each shared
cohort.

Usage::

    import ibis
    from benchmarks.compare_cohort_outputs import compare_cohort_outputs, print_comparison_report

    backend = ibis.duckdb.connect("benchmark_output/eunomia.duckdb")
    report = compare_cohort_outputs(
        backend, r_table="cohort", py_table="cohort_py",
    )
    print_comparison_report(report)

    # Optionally validate programmatically:
    assert report.n_cohorts_matched_exactly == report.n_cohorts_shared
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from circe.execution.typing import IbisBackendLike


@dataclass
class CohortMatchSummary:
    """Per-cohort row-level comparison result."""

    cohort_id: int
    """Cohort definition identifier."""

    n_r: int
    """Row count in the reference (R) table."""

    n_py: int
    """Row count in the Python table."""

    n_matched: int
    """Rows found identically in both tables."""

    n_only_r: int
    """Rows present only in the reference (R) table."""

    n_only_py: int
    """Rows present only in the Python table."""

    sample_only_r: list[tuple[int, str, str]] = field(default_factory=list)
    """Up to 3 sample rows from the reference table not found in Python."""

    sample_only_py: list[tuple[int, str, str]] = field(default_factory=list)
    """Up to 3 sample rows from the Python table not found in the reference."""

    @property
    def is_exact_match(self) -> bool:
        """True when the two implementations produce identical row sets."""
        return self.n_only_r == 0 and self.n_only_py == 0

    @property
    def pass_ratio(self) -> float:
        """Fraction of rows found in both implementations (0-1)."""
        denom = max(self.n_r, self.n_py)
        return self.n_matched / denom if denom > 0 else 1.0


@dataclass
class CohortComparisonReport:
    """Aggregate row-level comparison across implementations."""

    per_cohort: list[CohortMatchSummary]
    """Per-cohort comparison results."""

    n_cohorts_shared: int
    """Number of cohorts present in both tables."""

    n_cohorts_matched_exactly: int
    """Number of cohorts with zero row-level differences."""

    total_r_rows: int
    """Total row count in the reference table (all compared cohorts)."""

    total_py_rows: int
    """Total row count in the Python table (all compared cohorts)."""

    total_matched: int
    """Total matched rows across all compared cohorts."""

    total_only_r: int
    """Total rows only in the reference table."""

    total_only_py: int
    """Total rows only in the Python table."""

    @property
    def exact_match_pct(self) -> float:
        """Percentage of shared cohorts that match exactly."""
        return self.n_cohorts_matched_exactly / self.n_cohorts_shared * 100 if self.n_cohorts_shared else 0.0


def _read_cohort_table(
    backend: IbisBackendLike,
    table_name: str,
    schema: str | None,
    label: str,
) -> pd.DataFrame | None:
    """Read a cohort output table, cast columns to canonical types, return a DataFrame."""
    try:
        raw = backend.table(table_name, database=schema).execute()
    except Exception:
        print(f"  [WARN] {label} table '{table_name}' not found")
        return None

    if raw.empty:
        return None

    df = pd.DataFrame(
        {
            "cohort_definition_id": pd.to_numeric(raw["cohort_definition_id"], errors="coerce").astype(
                "int64"
            ),
            "subject_id": pd.to_numeric(raw["subject_id"], errors="coerce").astype("int64"),
            "cohort_start_date": pd.to_datetime(raw["cohort_start_date"], errors="coerce").dt.date,
            "cohort_end_date": pd.to_datetime(raw["cohort_end_date"], errors="coerce").dt.date,
        }
    )
    return df.drop_duplicates().dropna()


def _compare_single_cohort(
    cohort_id: int,
    r_rows: pd.DataFrame,
    py_rows: pd.DataFrame,
) -> CohortMatchSummary:
    """Compare row-level output for a single cohort."""
    key_cols = ["subject_id", "cohort_start_date", "cohort_end_date"]

    r_set = tuple(tuple(row) for row in r_rows[key_cols].itertuples(index=False))
    py_set = tuple(tuple(row) for row in py_rows[key_cols].itertuples(index=False))

    r_unique = set(r_set)
    py_unique = set(py_set)

    only_r = sorted(r_unique - py_unique)
    only_py = sorted(py_unique - r_unique)
    matched = r_unique & py_unique

    return CohortMatchSummary(
        cohort_id=cohort_id,
        n_r=len(r_unique),
        n_py=len(py_unique),
        n_matched=len(matched),
        n_only_r=len(only_r),
        n_only_py=len(only_py),
        sample_only_r=[(int(s), str(d), str(e)) for s, d, e in only_r[:3]],
        sample_only_py=[(int(s), str(d), str(e)) for s, d, e in only_py[:3]],
    )


def compare_cohort_outputs(
    backend: IbisBackendLike,
    r_table: str = "cohort",
    py_table: str = "cohort_py",
    schema: str | None = "main",
    *,
    cohort_ids: list[int] | None = None,
) -> CohortComparisonReport:
    """Compare row-level cohort output between two implementations.

    Args:
        backend: Ibis backend connection pointing at the database.
        r_table: Name of the reference (R/CohortGenerator) cohort output table.
        py_table: Name of the Python/circe cohort output table.
        schema: Database schema where both tables reside.
        cohort_ids: Specific cohort IDs to compare (``None`` = all shared).

    Returns:
        :class:`CohortComparisonReport` with per-cohort and aggregate results.
    """
    r_df = _read_cohort_table(backend, r_table, schema, "R")
    py_df = _read_cohort_table(backend, py_table, schema, "Py")

    if r_df is None or py_df is None:
        return CohortComparisonReport(
            per_cohort=[],
            n_cohorts_shared=0,
            n_cohorts_matched_exactly=0,
            total_r_rows=0,
            total_py_rows=0,
            total_matched=0,
            total_only_r=0,
            total_only_py=0,
        )

    r_ids = set(r_df["cohort_definition_id"].unique())
    py_ids = set(py_df["cohort_definition_id"].unique())

    shared = sorted(r_ids & py_ids & set(cohort_ids)) if cohort_ids is not None else sorted(r_ids & py_ids)

    per_cohort: list[CohortMatchSummary] = []
    total_r = 0
    total_py = 0
    total_m = 0
    total_o_r = 0
    total_o_py = 0
    exact_count = 0

    for cid in shared:
        r_rows = r_df[r_df["cohort_definition_id"] == cid]
        py_rows = py_df[py_df["cohort_definition_id"] == cid]
        summary = _compare_single_cohort(cid, r_rows, py_rows)
        per_cohort.append(summary)
        total_r += summary.n_r
        total_py += summary.n_py
        total_m += summary.n_matched
        total_o_r += summary.n_only_r
        total_o_py += summary.n_only_py
        if summary.is_exact_match:
            exact_count += 1

    return CohortComparisonReport(
        per_cohort=per_cohort,
        n_cohorts_shared=len(shared),
        n_cohorts_matched_exactly=exact_count,
        total_r_rows=total_r,
        total_py_rows=total_py,
        total_matched=total_m,
        total_only_r=total_o_r,
        total_only_py=total_o_py,
    )


def print_comparison_report(report: CohortComparisonReport) -> None:
    """Print a human-readable row-level parity report."""
    print("\nTable 6 — Row-level parity (R vs Python)")

    if report.n_cohorts_shared == 0:
        print("  No shared cohorts to compare.")
        return

    print(f"  Shared cohorts:     {report.n_cohorts_shared}")
    print(f"  Exactly matched:    {report.n_cohorts_matched_exactly} ({report.exact_match_pct:.1f}%)")
    print(f"  Total R rows:       {report.total_r_rows:,}")
    print(f"  Total Py rows:      {report.total_py_rows:,}")
    print(f"  Total matched:      {report.total_matched:,}")
    print(f"  Total only in R:    {report.total_only_r:,}")
    print(f"  Total only in Py:   {report.total_only_py:,}")

    mismatched = [c for c in report.per_cohort if not c.is_exact_match]
    if mismatched:
        print(f"\n  Cohort mismatches ({len(mismatched)}):")
        for c in mismatched:
            print(
                f"    {c.cohort_id:>5d}  "
                f"R={c.n_r:<6d}  Py={c.n_py:<6d}  "
                f"matched={c.n_matched:<6d}  "
                f"only_R={c.n_only_r:<4d}  only_Py={c.n_only_py:<4d}"
            )
            if c.sample_only_r:
                print(f"           samples only_R:  {c.sample_only_r[:3]}")
            if c.sample_only_py:
                print(f"           samples only_Py: {c.sample_only_py[:3]}")
    else:
        print(f"\n  ✓ All {report.n_cohorts_shared} shared cohorts match exactly.")
