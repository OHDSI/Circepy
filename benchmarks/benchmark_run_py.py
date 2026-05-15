#!/usr/bin/env python3
"""Runnable Python benchmark of PhenotypeLibrary cohorts.

Usage::

    # Export PhenotypeLibrary cohort JSONs (one-time setup)
    Rscript benchmarks/export_phenotypes.R

    # DuckDB (default — needs Eunomia DB from R)
    python benchmarks/benchmark_run_py.py

    # Databricks (set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN)
    python benchmarks/benchmark_run_py.py --backend databricks

Output (written to *benchmark_output/*)::

    py_checksum_times.csv  -- per-phenotype generation timing and status
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from _backend import connect_backend

from circe.cohort_definition_set import CohortDefinitionSet, generate_cohort_set
from circe.cohortdefinition import CohortExpression

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "benchmark_output"
JSON_DIR = OUTPUT_DIR / "phenotype_jsons"
MANIFEST_PATH = OUTPUT_DIR / "phenotype_manifest.csv"
RESULTS_CSV = OUTPUT_DIR / "py_checksum_times.csv"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Python circe cohort benchmark runner")
    p.add_argument(
        "--backend",
        default="duckdb",
        choices=("duckdb", "databricks"),
        help="Target database backend (default: duckdb)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    backend_label = args.backend

    # ── 1. Load phenotype definitions ────────────────────────────────────
    print("Loading phenotype definitions ...")
    if not MANIFEST_PATH.exists():
        print(
            f"  {MANIFEST_PATH} not found. Run 'Rscript benchmarks/export_phenotypes.R' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    manifest = pd.read_csv(MANIFEST_PATH)
    print(f"  Manifest has {len(manifest)} cohorts")

    cds = CohortDefinitionSet()
    skipped = 0
    for _, row in manifest.iterrows():
        cohort_id = int(row["cohortId"])
        cohort_name = str(row["cohortName"])
        json_path = JSON_DIR / f"{cohort_id}.json"
        if not json_path.exists():
            skipped += 1
            continue
        expression = CohortExpression.model_validate_json(json_path.read_text())
        cds.add(cohort_id=cohort_id, cohort_name=cohort_name, expression=expression)

    if skipped:
        print(f"  Skipped {skipped} cohorts with missing JSON files")
    print(f"  Loaded {len(cds)} cohorts into CohortDefinitionSet")

    # ── 2. Connect to backend ────────────────────────────────────────────
    print(f"Connecting to backend: {backend_label}")
    conn = connect_backend(backend_label)

    # ── 3. Generate cohorts ──────────────────────────────────────────────
    checksum_table = conn.py_checksum_table
    cohort_table = conn.py_cohort_table
    print(f"Generating cohorts (incremental) → {conn.results_schema}.{cohort_table}")
    results = generate_cohort_set(
        cds,
        backend=conn.backend,
        cdm_schema=conn.cdm_schema,
        cohort_table=cohort_table,
        results_schema=conn.results_schema,
        vocabulary_schema=conn.vocabulary_schema,
        incremental=True,
        checksum_table=checksum_table,
        stop_on_error=False,
    )

    # ── 4. Extract timing ────────────────────────────────────────────────
    print("Extracting timing ...")
    rows = []
    for r in results:
        generation_seconds = (r.end_time - r.start_time).total_seconds()
        rows.append(
            {
                "cohort_definition_id": r.cohort_id,
                "cohort_name": r.cohort_name,
                "checksum": r.checksum,
                "status": r.status,
                "generation_seconds": generation_seconds,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_CSV, index=False)
    print(f"  Wrote {len(df)} rows to {RESULTS_CSV}")

    # ── 5. Summary ────────────────────────────────────────────────────────
    complete_df = df[df["status"] == "COMPLETE"]
    failed_df = df[df["status"] == "FAILED"]
    skipped_df = df[df["status"] == "SKIPPED"]

    print(f"\n{'=' * 55}")
    print(f"Python benchmark complete (backend={backend_label})")
    print(f"  Phenotypes loaded : {len(manifest)}")
    print(f"  COMPLETE          : {len(complete_df)}")
    print(f"  FAILED            : {len(failed_df)}")
    print(f"  SKIPPED           : {len(skipped_df)}")
    if len(complete_df) > 0:
        print(f"  Total time (sum)  : {complete_df['generation_seconds'].sum():.4f}s")
        print(f"  Median per-cohort : {complete_df['generation_seconds'].median():.4f}s")
    print(f"  Timings written to : {RESULTS_CSV}")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()
