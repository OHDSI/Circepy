#!/usr/bin/env python3
"""Runnable Python benchmark of PhenotypeLibrary cohorts on Eunomia (DuckDB).

Usage::

    # Export PhenotypeLibrary cohort JSONs (one-time setup)
    Rscript benchmarks/export_phenotypes.R

    # Optional: create the Eunomia DuckDB (Python can also reuse R's)
    Rscript benchmarks/benchmark_run_r.R

    # Run the Python benchmark
    python benchmarks/benchmark_run_py.py

Output (written to *benchmark_output/*)::

    py_checksum_times.csv  -- per-phenotype generation timing and status
"""

from __future__ import annotations

import logging
from pathlib import Path

import ibis
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

from circe.cohort_definition_set import CohortDefinitionSet, generate_cohort_set
from circe.cohortdefinition import CohortExpression

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "benchmark_output"
JSON_DIR = OUTPUT_DIR / "phenotype_jsons"
MANIFEST_PATH = OUTPUT_DIR / "phenotype_manifest.csv"
DUCKDB_PATH = OUTPUT_DIR / "eunomia.duckdb"
RESULTS_CSV = OUTPUT_DIR / "py_checksum_times.csv"

COHORT_TABLE = "cohort_py"
CHECKSUM_TABLE = "cohort_py_checksum"
CDM_SCHEMA = "main"


def main() -> None:
    # ── 1. Load phenotype definitions ────────────────────────────────────
    print("Loading phenotype definitions ...")
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"{MANIFEST_PATH} not found. Run 'Rscript benchmarks/export_phenotypes.R' first."
        )

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

    # ── 2. Connect to DuckDB ─────────────────────────────────────────────
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(
            f"{DUCKDB_PATH} not found. Run 'Rscript benchmarks/benchmark_run_r.R' first."
        )
    print(f"Connecting to DuckDB: {DUCKDB_PATH}")
    backend = ibis.duckdb.connect(str(DUCKDB_PATH))

    # ── 3. Generate cohorts ──────────────────────────────────────────────
    print("Generating cohorts (incremental) ...")
    results = generate_cohort_set(
        cds,
        backend=backend,
        cdm_schema=CDM_SCHEMA,
        cohort_table=COHORT_TABLE,
        results_schema=CDM_SCHEMA,
        vocabulary_schema=CDM_SCHEMA,
        incremental=True,
        checksum_table=CHECKSUM_TABLE,
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
    print("Python benchmark complete")
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
