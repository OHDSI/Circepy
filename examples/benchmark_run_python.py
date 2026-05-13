#!/usr/bin/env python3
"""
benchmark_run_python.py

CircePy benchmark against a Databricks SQL warehouse.

What this script does:
  1. Downloads cohort metadata from OHDSI/PhenotypeLibrary on GitHub
  2. Downloads each CIRCE cohort JSON from the same repo
  3. Builds a CircePy CohortDefinitionSet from the downloaded definitions
  4. Calls generate_cohort_set() writing to DATABRICKS_SCRATCH_SCHEMA.cohort_python
  5. Runs a second incremental pass to benchmark checksum skipping
  6. Writes benchmark_output/python_results.csv

Prerequisites:
  - Fill in .env with DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN,
    DATABRICKS_SCRATCH_SCHEMA
  - CDM data at healthverity_cc.cdm_healthverity_cc_all_v3910

Usage:
    python examples/benchmark_run_python.py
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

import ibis
import pandas as pd
from dotenv import load_dotenv

from circe.api import (
    CohortDefinitionSet,
    cohort_expression_from_json,
    generate_cohort_set,
    summarise_generation_results,
)

# Ensure the repo root is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PHENOTYPE_META_URL = "https://raw.githubusercontent.com/OHDSI/PhenotypeLibrary/main/inst/Cohorts.csv"
PHENOTYPE_JSON_URL = (
    "https://raw.githubusercontent.com/OHDSI/PhenotypeLibrary/main/inst/cohorts/{cohort_id}.json"
)

OUTPUT_DIR = REPO_ROOT / "benchmark_output"
RESULTS_CSV = OUTPUT_DIR / "python_results.csv"

CDM_SCHEMA = "healthverity_cc.cdm_healthverity_cc_all_v3910"
SCRATCH_SCHEMA = os.environ["DATABRICKS_SCRATCH_SCHEMA"]
COHORT_TABLE = "cohort_python"
CHECKSUM_TABLE = "cohort_checksum_python"
N_COHORTS = 40  # number of cohorts to benchmark


# ---------------------------------------------------------------------------
# Step 1 — load phenotype library
# ---------------------------------------------------------------------------


def load_phenotypes() -> pd.DataFrame:
    """Download PhenotypeLibrary metadata and return rows with CIRCE JSON."""
    print("Downloading PhenotypeLibrary metadata...")
    meta = pd.read_csv(PHENOTYPE_META_URL)
    circe = meta[meta["isCirceJson"].astype(str).str.strip() == "1"].copy()
    circe = circe[["cohortId", "cohortName"]].dropna()
    circe["cohortId"] = circe["cohortId"].astype(int)
    print(f"  {len(circe)} CIRCE cohorts in library")
    return circe


def build_cohort_definition_set(meta: pd.DataFrame) -> tuple[CohortDefinitionSet, list]:
    """Download each cohort JSON and build a CohortDefinitionSet."""
    cds = CohortDefinitionSet()
    failures: list[tuple[int, str]] = []

    print(f"Downloading and parsing {len(meta)} cohort definitions...")
    for i, (_, row) in enumerate(meta.iterrows(), 1):
        cohort_id = int(row["cohortId"])
        cohort_name = str(row["cohortName"])
        url = PHENOTYPE_JSON_URL.format(cohort_id=cohort_id)

        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                json_str = resp.read().decode("utf-8")
            expression = cohort_expression_from_json(json_str)
            cds.add(cohort_id=cohort_id, cohort_name=cohort_name, expression=expression)
        except Exception as exc:
            failures.append((cohort_id, str(exc)))

        if i % 100 == 0 or i == len(meta):
            ok = i - len(failures)
            print(f"  {i}/{len(meta)}  parsed={ok}  failed={len(failures)}")

    return cds, failures


# ---------------------------------------------------------------------------
# Step 2 — connect to Databricks
# ---------------------------------------------------------------------------


def connect_databricks() -> ibis.BaseBackend:
    host = os.environ["DATABRICKS_HOST"]
    http_path = os.environ["DATABRICKS_HTTP_PATH"]
    token = os.environ["DATABRICKS_TOKEN"]

    # Parse catalog and schema from DATABRICKS_SCRATCH_SCHEMA (format: catalog.schema)
    parts = SCRATCH_SCHEMA.split(".", 1)
    catalog = parts[0] if len(parts) == 2 else None
    schema = parts[1] if len(parts) == 2 else parts[0]

    print(f"\nConnecting to Databricks: {host} (catalog={catalog}, schema={schema})")
    backend = ibis.databricks.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
        catalog=catalog,
        schema=schema,
    )
    print("  Connected.")
    return backend


# ---------------------------------------------------------------------------
# Step 3 — generate cohorts
# ---------------------------------------------------------------------------


def run_generation(cds: CohortDefinitionSet, backend: ibis.BaseBackend) -> tuple:
    # Run 1: full generation with incremental=True so checksums are saved
    # (no prior checksums exist, so nothing is skipped on this run)
    print(f"\nRun 1: generating {len(cds)} cohorts (full run, saves checksums)...")
    t0 = time.perf_counter()
    results_run1 = generate_cohort_set(
        cds,
        backend=backend,
        cdm_schema=CDM_SCHEMA,
        cohort_table=COHORT_TABLE,
        results_schema=SCRATCH_SCHEMA,
        incremental=True,
        checksum_table=CHECKSUM_TABLE,
        stop_on_error=False,
    )
    run1_seconds = time.perf_counter() - t0
    s1 = summarise_generation_results(results_run1)
    print(f"  {run1_seconds:.1f}s  COMPLETE={s1['COMPLETE']}  FAILED={s1['FAILED']}")

    # Run 2: incremental (all should be skipped)
    print("Run 2: incremental re-run (unchanged definitions — all should be skipped)...")
    t0 = time.perf_counter()
    results_run2 = generate_cohort_set(
        cds,
        backend=backend,
        cdm_schema=CDM_SCHEMA,
        cohort_table=COHORT_TABLE,
        results_schema=SCRATCH_SCHEMA,
        incremental=True,
        checksum_table=CHECKSUM_TABLE,
        stop_on_error=False,
    )
    run2_seconds = time.perf_counter() - t0
    s2 = summarise_generation_results(results_run2)
    speedup = run1_seconds / run2_seconds if run2_seconds > 0 else float("inf")
    print(f"  {run2_seconds:.2f}s  SKIPPED={s2['SKIPPED']}  speedup={speedup:.1f}x")

    return results_run1, run1_seconds, run2_seconds


# ---------------------------------------------------------------------------
# Step 4 — write results
# ---------------------------------------------------------------------------


def write_results(
    backend: ibis.BaseBackend,
    results_run1: list,
    parse_failures: list,
    meta: pd.DataFrame,
) -> None:
    cohort_df = backend.table(COHORT_TABLE, database=SCRATCH_SCHEMA).execute()
    row_counts = (
        cohort_df.groupby("cohort_definition_id")
        .size()
        .reset_index(name="row_count")
        .rename(columns={"cohort_definition_id": "cohortId"})
    )

    rows = []
    for r in results_run1:
        duration = (r.end_time - r.start_time).total_seconds()
        rc = row_counts.loc[row_counts["cohortId"] == r.cohort_id, "row_count"]
        rows.append(
            {
                "cohortId": r.cohort_id,
                "cohortName": r.cohort_name,
                "status": r.status,
                "generation_seconds": duration,
                "row_count": int(rc.iloc[0]) if len(rc) else 0,
                "checksum": r.checksum,
                "error": str(r.error) if r.error else "",
            }
        )

    for cohort_id, err in parse_failures:
        name_row = meta.loc[meta["cohortId"] == cohort_id, "cohortName"]
        rows.append(
            {
                "cohortId": cohort_id,
                "cohortName": name_row.iloc[0] if len(name_row) else "",
                "status": "PARSE_FAILED",
                "generation_seconds": 0,
                "row_count": 0,
                "checksum": "",
                "error": err,
            }
        )

    pd.DataFrame(rows).to_csv(RESULTS_CSV, index=False)
    print(f"\nResults written to {RESULTS_CSV}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    meta = load_phenotypes().head(N_COHORTS)
    backend = connect_databricks()
    cds, parse_failures = build_cohort_definition_set(meta)

    print(f"\nCohortDefinitionSet: {len(cds)} cohorts  ({len(parse_failures)} parse failures)")
    print(f"CDM schema     : {CDM_SCHEMA}")
    print(f"Cohort schema  : {SCRATCH_SCHEMA}")

    results_run1, run1_s, run2_s = run_generation(cds, backend)
    write_results(backend, results_run1, parse_failures, meta)

    s = summarise_generation_results(results_run1)
    total = len(meta)
    print(f"\n{'=' * 55}")
    print("CircePy benchmark complete")
    print(f"  Total phenotypes          : {total}")
    print(f"  Parse failures            : {len(parse_failures)}")
    print(f"  Generation COMPLETE       : {s['COMPLETE']}")
    print(f"  Generation FAILED         : {s['FAILED']}")
    print(f"  Full run time             : {run1_s:.1f}s")
    print(f"  Incremental run time      : {run2_s:.2f}s  ({run1_s / run2_s:.1f}x speedup)")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
