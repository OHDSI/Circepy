"""Compare era-cache prevalence against FeatureExtraction output.

Reads FeatureExtraction ``covariates.csv`` files produced by ``run_fe_detailed.R``
and the era cache, and writes a parity report as JSON and Markdown.

Usage::

    python benchmark/fe_parity_compare.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pandas as pd  # noqa: E402

from circe.era_cache import (  # noqa: E402
    CohortEraSpec,
    EraFeatureSpec,
    era_feature_key,
    load_cohort,
    prevalence,
)
from circe.era_cache.schema import LARGE_TABLES  # noqa: E402
from circe.era_cache.spark_backend import ThriftBackend  # noqa: E402

FEATURES = {
    "Type 2 diabetes": 201826,
    "Heart failure": 316139,
    "Obesity": 433736,
    "Asthma": 317009,
    "Chronic kidney disease": 46271022,
    "COPD": 255573,
}

COHORTS = {
    "first T2DM": 201826,
    "first obesity": 433736,
    "first CKD": 46271022,
    "first asthma": 317009,
}

WINDOWS = {"365": -365, "90": -90}

OUTPUT = Path("/tmp/era_bench")
CACHE = "cdm_era_cache"
CDM = "cdm"


def feature_key(concept_id: int) -> str:
    return era_feature_key(
        EraFeatureSpec(name="f", source_table="condition_occurrence", concept_ids=(concept_id,))
    )


def read_fe(directory: Path) -> dict[int, dict[str, float]]:
    path = directory / "covariates.csv"
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    return {
        int(str(row.covariateId)[:-3]): {
            "numerator": int(row.sumValue),
            "average": float(row.averageValue),
        }
        for row in frame.itertuples(index=False)
    }


def main() -> int:
    backend = ThriftBackend()
    backend.no_broadcast_tables.update(LARGE_TABLES)
    key_to_concept = {feature_key(c): c for c in FEATURES.values()}
    observation_period = backend.table("observation_period", CDM)

    rows = []
    for cohort_name, cohort_concept in COHORTS.items():
        cohort_table = f"coh_{cohort_concept}"
        if cohort_table not in backend.execute_raw(f"SHOW TABLES IN {CACHE}")["tableName"].tolist():
            continue
        relation = load_cohort(backend.table(cohort_table, CACHE), cohort_id=1)
        size = int(backend.execute_raw(f"SELECT COUNT(*) n FROM {CACHE}.{cohort_table}").iloc[0]["n"])
        for window_label, start in WINDOWS.items():
            directory = (
                Path("/tmp/fe_det_365")
                if cohort_name == "first T2DM" and window_label == "365"
                else Path(f"/tmp/fe_det_{cohort_concept}_{start}")
            )
            fe = read_fe(directory)
            if not fe:
                continue
            cached = backend.execute(
                prevalence(
                    relation,
                    windows=[CohortEraSpec(start, 0)],
                    backend=backend,
                    cache_schema=CACHE,
                    observation_period=observation_period,
                )
            )
            mine = {
                key_to_concept[row.feature_key]: int(row.numerator)
                for row in cached.itertuples(index=False)
                if row.feature_key in key_to_concept
            }
            for name, concept_id in FEATURES.items():
                obtained = mine.get(concept_id)
                expected = fe.get(concept_id, {}).get("numerator")
                rows.append(
                    {
                        "cohort": cohort_name,
                        "cohort_size": size,
                        "window": f"{window_label} days prior",
                        "feature": name,
                        "concept_id": concept_id,
                        "era_cache_numerator": obtained,
                        "feature_extraction_numerator": expected,
                        "era_cache_prevalence": round(obtained / size, 6) if obtained else 0.0,
                        "feature_extraction_prevalence": round(expected / size, 6) if expected else 0.0,
                        "absolute_difference": abs((obtained or 0) - (expected or 0)),
                        "exact_match": obtained == expected,
                    }
                )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "fe_parity.json").write_text(json.dumps(rows, indent=2))

    total = len(rows)
    matches = sum(1 for row in rows if row["exact_match"])
    print(f"{matches}/{total} comparisons matched exactly")
    for row in rows:
        flag = "" if row["exact_match"] else "  <-- MISMATCH"
        print(
            f"{row['cohort']:14s} {row['window']:15s} {row['feature']:24s} "
            f"{row['era_cache_numerator']:>8} {row['feature_extraction_numerator']:>8}{flag}"
        )
    return 0 if matches == total else 1


if __name__ == "__main__":
    sys.exit(main())
