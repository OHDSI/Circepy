from __future__ import annotations

from pathlib import Path

import pytest

from circe.cohortdefinition import CohortExpression
from circe.execution.api import build_cohort
from circe.execution.ibis.codesets import build_single_codeset_table
from circe.execution.normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem

BENCHMARK_OUTPUT = Path(__file__).resolve().parent.parent.parent / "benchmark_output"
JSON_DIR = Path(__file__).resolve().parent / "phenotype_fixtures"


def _seed_minimal_cdm(conn, ibis):
    import datetime

    S = datetime.date(2000, 1, 1)
    tables = {
        "person": {"person_id": [999], "year_of_birth": [1900], "gender_concept_id": [0]},
        "observation_period": {
            "person_id": [999],
            "observation_period_id": [999],
            "observation_period_start_date": [S],
            "observation_period_end_date": [S],
        },
        "condition_occurrence": {
            "person_id": [999],
            "condition_occurrence_id": [999],
            "condition_concept_id": [0],
            "condition_start_date": [S],
            "condition_end_date": [S],
        },
        "procedure_occurrence": {
            "person_id": [999],
            "procedure_occurrence_id": [999],
            "procedure_concept_id": [0],
            "procedure_date": [S],
        },
        "measurement": {
            "person_id": [999],
            "measurement_id": [999],
            "measurement_concept_id": [0],
            "measurement_date": [S],
        },
        "observation": {
            "person_id": [999],
            "observation_id": [999],
            "observation_concept_id": [0],
            "observation_date": [S],
        },
        "drug_exposure": {
            "person_id": [999],
            "drug_exposure_id": [999],
            "drug_concept_id": [0],
            "drug_exposure_start_date": [S],
            "drug_exposure_end_date": [S],
        },
        "death": {"person_id": [999], "death_date": [S]},
        "visit_occurrence": {
            "person_id": [999],
            "visit_occurrence_id": [999],
            "visit_concept_id": [0],
            "visit_start_date": [S],
            "visit_end_date": [S],
        },
        "specimen": {
            "person_id": [999],
            "specimen_id": [999],
            "specimen_concept_id": [0],
            "specimen_date": [S],
        },
        "device_exposure": {
            "person_id": [999],
            "device_exposure_id": [999],
            "device_concept_id": [0],
            "device_exposure_start_date": [S],
            "device_exposure_end_date": [S],
        },
        "dose_era": {
            "person_id": [999],
            "dose_era_id": [999],
            "drug_concept_id": [0],
            "unit_concept_id": [0],
            "dose_value": [0.0],
            "dose_era_start_date": [S],
            "dose_era_end_date": [S],
        },
        "payer_plan_period": {
            "person_id": [999],
            "payer_plan_period_id": [999],
            "payer_plan_period_start_date": [S],
            "payer_plan_period_end_date": [S],
        },
        "visit_detail": {
            "person_id": [999],
            "visit_detail_id": [999],
            "visit_detail_concept_id": [0],
            "visit_detail_start_date": [S],
            "visit_detail_end_date": [S],
        },
        "condition_era": {
            "person_id": [999],
            "condition_era_id": [999],
            "condition_concept_id": [0],
            "condition_era_start_date": [S],
            "condition_era_end_date": [S],
            "condition_occurrence_count": [1],
        },
        "drug_era": {
            "person_id": [999],
            "drug_era_id": [999],
            "drug_concept_id": [0],
            "drug_era_start_date": [S],
            "drug_era_end_date": [S],
            "drug_exposure_count": [1],
            "gap_days": [0],
        },
        "concept": {"concept_id": [0, 999], "invalid_reason": ["X", None]},
        "concept_ancestor": {"ancestor_concept_id": [999], "descendant_concept_id": [999]},
        "concept_relationship": {
            "concept_id_1": [999],
            "concept_id_2": [999],
            "relationship_id": ["X"],
            "invalid_reason": ["X"],
        },
    }
    for name, obj in tables.items():
        conn.create_table(name, obj=ibis.memtable(obj), overwrite=True)


def _make_item(cid: int, *, excluded: bool = False) -> NormalizedConceptSetItem:
    return NormalizedConceptSetItem(
        concept_id=cid,
        is_excluded=excluded,
        include_descendants=False,
        include_mapped=False,
    )


# ------------------------------------------------------------------
# Multi-exclude collision tests
# ------------------------------------------------------------------


def test_multiple_excludes_no_collision():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    concept_sets = {
        1: NormalizedConceptSet(
            set_id=1,
            items=(
                _make_item(111),
                _make_item(222),
                _make_item(333, excluded=True),
                _make_item(444, excluded=True),
                _make_item(555, excluded=True),
            ),
        ),
    }

    tbl = build_single_codeset_table(
        backend=conn,
        concept_sets=concept_sets,
        batch_table_name="__test_exclude_codesets",
    )
    rows = tbl.execute()
    assert set(rows["concept_id"].tolist()) == {111, 222}
    conn.drop_table("__test_exclude_codesets", force=True)


def test_single_exclude_works():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    concept_sets = {
        1: NormalizedConceptSet(
            set_id=1,
            items=(_make_item(111), _make_item(222), _make_item(333, excluded=True)),
        ),
    }

    tbl = build_single_codeset_table(
        backend=conn, concept_sets=concept_sets, batch_table_name="__test_exclude_codesets2"
    )
    rows = tbl.execute()
    assert set(rows["concept_id"].tolist()) == {111, 222}
    conn.drop_table("__test_exclude_codesets2", force=True)


def test_all_excluded_returns_empty():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    concept_sets = {
        1: NormalizedConceptSet(
            set_id=1,
            items=(
                _make_item(111, excluded=True),
                _make_item(222, excluded=True),
                _make_item(333, excluded=True),
            ),
        ),
    }

    tbl = build_single_codeset_table(
        backend=conn, concept_sets=concept_sets, batch_table_name="__test_exclude_codesets3"
    )
    rows = tbl.execute()
    assert len(rows) == 0
    conn.drop_table("__test_exclude_codesets3", force=True)


# ------------------------------------------------------------------
# Phenotype cohort regression tests (recursion / collision fixes)
# ------------------------------------------------------------------


@pytest.mark.parametrize("cohort_id", [33, 54])
def test_phenotype_cohort_with_exclusions_compiles(cohort_id: int):
    """Cohorts 33 and 54 previously failed with recursion errors."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    json_path = JSON_DIR / f"{cohort_id}.json"
    if not json_path.exists():
        pytest.skip(f"Phenotype JSON not found: {json_path}")

    expression = CohortExpression.model_validate_json(json_path.read_text())

    conn = ibis.duckdb.connect()
    _seed_minimal_cdm(conn, ibis)

    try:
        build_cohort(expression, backend=conn, cdm_schema="main", materialize=False)
    except Exception as exc:
        pytest.fail(f"Cohort {cohort_id} compilation failed: {exc}")
