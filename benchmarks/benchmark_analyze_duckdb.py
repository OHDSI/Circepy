#!/usr/bin/env python3
"""Analyse R and Python benchmark results side-by-side.

Reads the checksum timing CSVs produced by
:file:`benchmarks/benchmark_run_r.R` and :file:`benchmarks/benchmark_run_py.py`,
queries the persisted history tables directly from the database for
cross-validation, and prints a paper-ready comparative summary.

Usage::

    python benchmarks/benchmark_analyze_duckdb.py                    # DuckDB
    python benchmarks/benchmark_analyze_duckdb.py --backend databricks
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from _backend import PY_CSV, R_CSV, connect_backend
from compare_cohort_outputs import compare_cohort_outputs, print_comparison_report

REPO_ROOT = Path(__file__).resolve().parent.parent


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CircePy benchmark result analyzer")
    p.add_argument(
        "--backend",
        default="duckdb",
        choices=("duckdb", "databricks"),
        help="Target database backend for cross-validation (default: duckdb)",
    )
    return p.parse_args()


def load_csv(path: Path) -> pd.DataFrame | None:
    """Load a benchmark timing CSV, returning None if it does not exist."""
    if not path.exists():
        print(f"  [WARN] {path} not found — skipping")
        return None
    return pd.read_csv(path)


def _has_status(df: pd.DataFrame) -> bool:
    return "status" in df.columns


def print_coverage(label: str, df: pd.DataFrame) -> None:
    n = len(df)
    if _has_status(df):
        n_ok = (df["status"] == "COMPLETE").sum()
        n_fail = (df["status"] == "FAILED").sum()
        n_skip = (df["status"] == "SKIPPED").sum()
        print(f"  {label}: {n} cohorts — {n_ok} COMPLETE, {n_fail} FAILED, {n_skip} SKIPPED")
    else:
        print(f"  {label}: {n} cohorts (checksum table — all assumed COMPLETE)")


def print_timing(label: str, df: pd.DataFrame) -> None:
    complete = df[df["status"] == "COMPLETE"] if _has_status(df) else df
    if complete.empty:
        print(f"  {label}: no completed cohorts to report timing")
        return
    secs = complete["generation_seconds"]
    print(f"  {label} timing (n={len(secs)}):")
    print(f"    Total : {secs.sum():.4f}s")
    print(f"    Mean  : {secs.mean():.4f}s")
    print(f"    Median: {secs.median():.4f}s")
    print(f"    Std   : {secs.std():.4f}s")
    print(f"    Min   : {secs.min():.4f}s")
    print(f"    Max   : {secs.max():.4f}s")


def cross_validate(
    label: str,
    csv_df: pd.DataFrame,
    conn,
    cohort_table: str,
    checksum_table: str,
) -> None:
    """Read the persisted checksum table and compare with the CSV."""
    try:
        history = conn.backend.table(checksum_table, database=conn.results_schema).execute()
    except Exception:
        print(f"  {label} cross-validation: checksum table '{checksum_table}' not found")
        return

    if history.empty:
        print(f"  {label} cross-validation: checksum table is empty")
        return

    complete_csv = csv_df[csv_df["status"] == "COMPLETE"] if _has_status(csv_df) else csv_df
    if complete_csv.empty:
        return

    history_complete = history[history["status"] == "COMPLETE"] if _has_status(history) else history
    print(f"  {label} cross-validation:")
    print(f"    CSV rows            : {len(complete_csv)}")
    print(f"    DB rows             : {len(history_complete)}")

    csv_total = complete_csv["generation_seconds"].sum()
    if "start_time" in history_complete.columns and "end_time" in history_complete.columns:
        starts = history_complete["start_time"]
        ends = history_complete["end_time"]
        if pd.api.types.is_datetime64_any_dtype(starts):
            db_total = (ends - starts).dt.total_seconds().sum()
        else:
            db_total = ((ends.astype(float) - starts.astype(float)) / 1000.0).sum()
        delta = abs(csv_total - db_total)
        print(f"    CSV total time     : {csv_total:.4f}s")
        print(f"    DB total time      : {db_total:.4f}s")
        print(f"    Delta              : {delta:.4f}s {'✓' if delta < 1.0 else '✗'}")


def print_cohort_row_counts(label: str, conn, cohort_table: str) -> None:
    """Print row count summary from the cohort output table."""
    try:
        rows = conn.backend.table(cohort_table, database=conn.results_schema).execute()
    except Exception:
        print(f"  {label} row counts: table '{cohort_table}' not found")
        return
    if rows.empty:
        print(f"  {label}: no cohort rows")
        return
    counts = rows.groupby("cohort_definition_id").size()
    print(f"  {label} row counts: {len(counts)} cohorts, {counts.sum()} total rows")
    print(f"    Mean per cohort: {counts.mean():.1f}")


def compare_shared(label_prefix: str, r_df: pd.DataFrame, py_df: pd.DataFrame) -> None:
    """Compare timing for cohorts present in both runs."""
    r_complete = r_df[r_df["status"] == "COMPLETE"].copy() if _has_status(r_df) else r_df.copy()
    py_complete = py_df[py_df["status"] == "COMPLETE"].copy() if _has_status(py_df) else py_df.copy()
    if r_complete.empty or py_complete.empty:
        return

    r_lookup = r_complete.set_index("cohort_definition_id")["generation_seconds"]
    py_lookup = py_complete.set_index("cohort_definition_id")["generation_seconds"]
    shared = r_lookup.index.intersection(py_lookup.index)
    if len(shared) < 2:
        return

    r_shared = r_lookup[shared]
    py_shared = py_lookup[shared]
    ratio = (py_shared / r_shared.replace(0, float("nan"))).dropna()
    ratio = ratio.replace([float("inf"), -float("inf")], float("nan")).dropna()

    print(f"\n  {label_prefix} per-cohort comparison ({len(shared)} shared cohorts):")
    print(f"    R total (shared)   : {r_shared.sum():.4f}s")
    print(f"    Py total (shared)  : {py_shared.sum():.4f}s")
    print(f"    R mean (shared)    : {r_shared.mean():.4f}s")
    print(f"    Py mean (shared)   : {py_shared.mean():.4f}s")
    if len(ratio) > 0:
        print(f"    Py/R ratio median  : {ratio.median():.2f}x")


def main() -> None:
    args = _parse_args()
    backend_label = args.backend

    print("=" * 60)
    print(f"R vs Python CohortGenerator Benchmark Comparison (backend={backend_label})")
    print("=" * 60)

    r_df = load_csv(R_CSV)
    py_df = load_csv(PY_CSV)

    if r_df is None and py_df is None:
        print("\nNo benchmark results found. Run the benchmarks first:")
        print("  Rscript benchmarks/benchmark_run_r.R")
        print("  python benchmarks/benchmark_run_py.py")
        return

    # ── Coverage ────────────────────────────────────────────────────────
    print("\nTable 1 — Coverage")
    if r_df is not None:
        print_coverage("R ", r_df)
    if py_df is not None:
        print_coverage("Py", py_df)

    # ── Generation timing ────────────────────────────────────────────────
    print("\nTable 2 — Generation timing")
    if r_df is not None:
        print_timing("R ", r_df)
    if py_df is not None:
        print_timing("Py", py_df)

    # ── Cross-validation & row counts (needs a backend connection) ──────
    print("\nTable 3 — Cross-validation (CSV vs persisted checksum table)")
    try:
        conn = connect_backend(backend_label)
    except Exception as exc:
        print(f"  Cannot connect to {backend_label}: {exc}")
        conn = None

    if conn is not None:
        if r_df is not None:
            cross_validate("R ", r_df, conn, conn.r_cohort_table, conn.r_checksum_table)
        if py_df is not None:
            cross_validate("Py", py_df, conn, conn.py_cohort_table, conn.py_checksum_table)

        print("\nTable 4 — Cohort row counts")
        if r_df is not None:
            print_cohort_row_counts("R ", conn, conn.r_cohort_table)
        if py_df is not None:
            print_cohort_row_counts("Py", conn, conn.py_cohort_table)

        print("\nTable 6 — Row-level parity (R vs Python)")
        report = compare_cohort_outputs(
            conn.backend,
            r_table=conn.r_cohort_table,
            py_table=conn.py_cohort_table,
            schema=conn.results_schema,
        )
        print_comparison_report(report)

    # ── R vs Python shared-cohort comparison ─────────────────────────────
    if r_df is not None and py_df is not None:
        print("\nTable 5 — R vs Python shared-cohort comparison")
        compare_shared("=>", r_df, py_df)

    print(f"\n{'=' * 60}")
    print("Analysis complete")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
