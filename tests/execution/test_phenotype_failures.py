"""Regression tests for PhenotypeLibrary cohorts that previously failed.

These are the 3 most complex cohorts in the PhenotypeLibrary (51-97 primary
criteria, 105 concept sets, 7-9 inclusion rules, multiple censoring criteria).
They failed because the sequential ``_union_all`` produced deeply nested
UNION ALL expressions that exceeded DuckDB's query compilation limits.

The binary-tree merge in ``_union_all`` reduces nesting from O(n) to O(log n).

These tests verify that ``build_cohort`` (compilation) succeeds.  Full
``generate_cohort_set`` is covered by ``pytest.mark.slow`` tests.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from circe.cohortdefinition import CohortExpression
from circe.execution.api import build_cohort

BENCHMARK_OUTPUT = Path(__file__).resolve().parent.parent.parent / "benchmark_output"
JSON_DIR = BENCHMARK_OUTPUT / "phenotype_jsons"

D = datetime.date  # shorthand


def _seed_minimal_cdm(conn, ibis):
    """Minimal CDM tables so cohort compilation doesn't fail on missing tables.
    Uses sentinel person_id=999 so no actual rows match real cohort criteria."""
    S = D(2000, 1, 1)  # sentinel date
    conn.create_table(
        "person",
        obj=ibis.memtable({"person_id": [999], "year_of_birth": [1900], "gender_concept_id": [0]}),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "observation_period_id": [999],
                "observation_period_start_date": [S],
                "observation_period_end_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "condition_occurrence_id": [999],
                "condition_concept_id": [0],
                "condition_start_date": [S],
                "condition_end_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "procedure_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "procedure_occurrence_id": [999],
                "procedure_concept_id": [0],
                "procedure_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "measurement",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "measurement_id": [999],
                "measurement_concept_id": [0],
                "measurement_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "observation_id": [999],
                "observation_concept_id": [0],
                "observation_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "drug_exposure_id": [999],
                "drug_concept_id": [0],
                "drug_exposure_start_date": [S],
                "drug_exposure_end_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table("death", obj=ibis.memtable({"person_id": [999], "death_date": [S]}), overwrite=True)
    conn.create_table(
        "visit_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "visit_occurrence_id": [999],
                "visit_concept_id": [0],
                "visit_start_date": [S],
                "visit_end_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "specimen",
        obj=ibis.memtable(
            {"person_id": [999], "specimen_id": [999], "specimen_concept_id": [0], "specimen_date": [S]}
        ),
        overwrite=True,
    )
    conn.create_table(
        "device_exposure",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "device_exposure_id": [999],
                "device_concept_id": [0],
                "device_exposure_start_date": [S],
                "device_exposure_end_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "dose_era",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "dose_era_id": [999],
                "drug_concept_id": [0],
                "unit_concept_id": [0],
                "dose_value": [0.0],
                "dose_era_start_date": [S],
                "dose_era_end_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "payer_plan_period",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "payer_plan_period_id": [999],
                "payer_plan_period_start_date": [S],
                "payer_plan_period_end_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "visit_detail",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "visit_detail_id": [999],
                "visit_detail_concept_id": [0],
                "visit_detail_start_date": [S],
                "visit_detail_end_date": [S],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_era",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "condition_era_id": [999],
                "condition_concept_id": [0],
                "condition_era_start_date": [S],
                "condition_era_end_date": [S],
                "condition_occurrence_count": [1],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "drug_era",
        obj=ibis.memtable(
            {
                "person_id": [999],
                "drug_era_id": [999],
                "drug_concept_id": [0],
                "drug_era_start_date": [S],
                "drug_era_end_date": [S],
                "drug_exposure_count": [1],
                "gap_days": [0],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept", obj=ibis.memtable({"concept_id": [0, 999], "invalid_reason": ["X", None]}), overwrite=True
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable({"ancestor_concept_id": [999], "descendant_concept_id": [999]}),
        overwrite=True,
    )
    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable(
            {"concept_id_1": [999], "concept_id_2": [999], "relationship_id": ["X"], "invalid_reason": ["X"]}
        ),
        overwrite=True,
    )


# The 3 persistently failing PhenotypeLibrary cohorts
FAILING_COHORT_IDS = [1432, 1433, 1434]


@pytest.mark.parametrize("cohort_id", FAILING_COHORT_IDS)
def test_phenotype_cohort_compiles(cohort_id: int) -> None:
    """Cohorts 1432-1434 (87, 97, 51 primary criteria) must compile successfully.

    Compilation exercises ``_union_all`` which previously produced O(n) nested
    UNION ALL expressions that crashed DuckDB.  The binary-tree merge reduces
    nesting to O(log n).
    """
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    json_path = JSON_DIR / f"{cohort_id}.json"
    if not json_path.exists():
        pytest.skip(f"Phenotype JSON not found: {json_path}")

    expression = CohortExpression.model_validate_json(json_path.read_text())

    conn = ibis.duckdb.connect()
    _seed_minimal_cdm(conn, ibis)

    # build_cohort exercises the full UNION ALL path; materialize=False
    # keeps this compile-only (no temp tables created).
    try:
        build_cohort(expression, backend=conn, cdm_schema="main", materialize=False)
    except Exception as exc:
        pytest.fail(f"Cohort {cohort_id} compilation failed: {exc}")
