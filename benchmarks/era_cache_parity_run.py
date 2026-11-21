"""Two-part benchmark: equivalence, then timing.

The Spark Thrift session drops long-running statements on this server, so the
work is split into many short statements and results are written incrementally.

Usage::

    python benchmarks/era_cache_parity_run.py equivalence   # writes equivalence.json
    python benchmarks/era_cache_parity_run.py timing        # writes timings.json
    python benchmarks/era_cache_parity_run.py scale         # writes scale.json
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circe.era_cache import (  # noqa: E402
    CohortEraSpec,
    EraFeatureSpec,
    build_era_cache,
    era_feature_key,
    load_cohort,
    prevalence,
)
from circe.era_cache.schema import LARGE_TABLES  # noqa: E402
from circe.era_cache.spark_backend import ThriftBackend  # noqa: E402

OUT = Path("/tmp/era_bench")
CDM = "cdm"
VOCAB = "vocab"
CACHE = "cdm_era_cache"

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
WINDOWS = [("1 year prior", -365, 0), ("90 days prior", -90, 0)]


def backend() -> ThriftBackend:
    b = ThriftBackend()
    b.no_broadcast_tables.update(LARGE_TABLES)
    return b


def spec(name: str, concept_id: int) -> EraFeatureSpec:
    return EraFeatureSpec(name=name, source_table="condition_occurrence", concept_ids=(concept_id,))


def ensure_cache(b: ThriftBackend):
    return build_era_cache(
        [spec(n, c) for n, c in FEATURES.items()],
        backend=b,
        cache_schema=CACHE,
        cdm_schema=CDM,
        vocabulary_schema=VOCAB,
    )


def cohort_table_name(cohort_concept: int) -> str:
    return f"coh_{cohort_concept}"


def ensure_cohort(b: ThriftBackend, cohort_concept: int) -> str:
    """First occurrence in 2008-2009 with one year of follow-up (idempotent)."""
    table = cohort_table_name(cohort_concept)
    existing = b.execute_raw(f"SHOW TABLES IN {CACHE}").get("tableName", [])
    if table in list(existing):
        return table
    key = era_feature_key(spec("c", cohort_concept))
    b.raw_sql(
        f"CREATE TABLE {CACHE}.{table} USING DELTA AS "
        "SELECT 1 AS cohort_definition_id, t.subject_id, t.first_date AS cohort_start_date, "
        "DATE_ADD(t.first_date, 365) AS cohort_end_date FROM ("
        f"SELECT e.subject_id, MIN(e.era_start) AS first_date FROM {CACHE}.era_feature_presence e "
        f"WHERE e.feature_key = '{key}' GROUP BY e.subject_id) t "
        "WHERE t.first_date >= DATE'2008-01-01' AND t.first_date <= DATE'2009-12-31'"
    )
    return table


def cached_prevalence(b, table, start, end):
    relation = load_cohort(b.table(table, CACHE), cohort_id=1)
    frame = b.execute(
        prevalence(
            relation,
            windows=[CohortEraSpec(start, end)],
            backend=b,
            cache_schema=CACHE,
            observation_period=b.table("observation_period", CDM),
        )
    )
    return {str(r["feature_key"]): int(r["numerator"]) for _, r in frame.iterrows()}


def direct_prevalence(b, table, concept_id, start, end) -> int:
    lower = "DATE'1900-01-01'" if start is None else f"DATE_ADD(c.cohort_start_date, {start})"
    upper = f"DATE_ADD(c.cohort_start_date, {end})"
    sql = f"""
    SELECT COUNT(DISTINCT c.subject_id) AS n
    FROM {CACHE}.{table} c
    JOIN {CDM}.condition_occurrence co
      ON co.person_id = c.subject_id AND co.condition_concept_id = {concept_id}
    WHERE co.condition_start_date <= {upper}
      AND COALESCE(co.condition_end_date, co.condition_start_date) >= {lower}
    """
    return int(b.execute_raw(sql).iloc[0]["n"])


def section_equivalence() -> None:
    b = backend()
    ensure_cache(b)
    report = []
    for cohort_name, cohort_concept in COHORTS.items():
        table = ensure_cohort(b, cohort_concept)
        size = int(b.execute_raw(f"SELECT COUNT(*) n FROM {CACHE}.{table}").iloc[0]["n"])
        for label, start, end in WINDOWS:
            cached = cached_prevalence(b, table, start, end)
            rows = []
            for name, concept_id in FEATURES.items():
                key = era_feature_key(spec(name, concept_id))
                direct = direct_prevalence(b, table, concept_id, start, end)
                got = cached.get(key, 0)
                rows.append(
                    {
                        "feature": name,
                        "cached": got,
                        "direct": direct,
                        "equal": got == direct,
                    }
                )
            report.append(
                {
                    "cohort": cohort_name,
                    "cohort_size": size,
                    "window": label,
                    "start": start,
                    "end": end,
                    "all_equal": all(r["equal"] for r in rows),
                    "features": rows,
                }
            )
            print(
                f"{cohort_name:14s} {label:14s} equal={report[-1]['all_equal']}",
                flush=True,
            )
    (OUT / "equivalence.json").write_text(json.dumps(report, indent=2))
    print("ALL EQUAL:", all(r["all_equal"] for r in report))


def section_timing() -> None:
    b = backend()
    timings = []
    table = ensure_cohort(b, COHORTS["first T2DM"])
    relation = load_cohort(b.table(table, CACHE), cohort_id=1)
    op = b.table("observation_period", CDM)

    for repeat in range(3):
        # warm build
        started = time.perf_counter()
        ensure_cache(b)
        warm = time.perf_counter() - started

        # cached read for all features and both windows
        started = time.perf_counter()
        b.execute(
            prevalence(
                relation,
                windows=[CohortEraSpec(s, e) for _l, s, e in WINDOWS],
                backend=b,
                cache_schema=CACHE,
                observation_period=op,
            )
        )
        cached = time.perf_counter() - started

        # direct: one statement per (feature, window)
        started = time.perf_counter()
        for _name, concept_id in FEATURES.items():
            for _label, s, e in WINDOWS:
                direct_prevalence(b, table, concept_id, s, e)
        direct = time.perf_counter() - started

        timings.append(
            {
                "repeat": repeat,
                "warm_build_seconds": round(warm, 2),
                "cached_read_seconds": round(cached, 2),
                "direct_read_seconds": round(direct, 2),
                "speedup": round(direct / cached, 2) if cached else None,
            }
        )
        print(timings[-1], flush=True)

    (OUT / "timings.json").write_text(json.dumps(timings, indent=2))
    cached_mean = statistics.mean(t["cached_read_seconds"] for t in timings)
    direct_mean = statistics.mean(t["direct_read_seconds"] for t in timings)
    print(
        f"mean cached {cached_mean:.2f}s mean direct {direct_mean:.2f}s -> {direct_mean / cached_mean:.1f}x"
    )


def section_scale(n_features: int = 20, repeats: int = 2) -> None:
    b = backend()
    frame = b.execute_raw(
        f"SELECT condition_concept_id, COUNT(*) n FROM {CDM}.condition_occurrence "
        f"WHERE condition_concept_id > 0 GROUP BY 1 ORDER BY n DESC LIMIT {n_features}"
    )
    specs = [
        spec(f"c{int(row['condition_concept_id'])}", int(row["condition_concept_id"]))
        for _, row in frame.iterrows()
    ]
    built = build_era_cache(specs, backend=b, cache_schema=CACHE, cdm_schema=CDM, vocabulary_schema=VOCAB)
    keys = {era_feature_key(s): s.concept_ids[0] for s in specs}
    table = ensure_cohort(b, COHORTS["first T2DM"])
    relation = load_cohort(b.table(table, CACHE), cohort_id=1)
    op = b.table("observation_period", CDM)
    windows = [CohortEraSpec(s, e) for _l, s, e in WINDOWS]

    results = []
    for repeat in range(repeats):
        started = time.perf_counter()
        cached_frame = b.execute(
            prevalence(
                relation,
                windows=windows,
                backend=b,
                cache_schema=CACHE,
                observation_period=op,
            )
        )
        cached = time.perf_counter() - started
        cached_map = {
            (str(r["feature_key"]), int(r["window_index"])): int(r["numerator"])
            for _, r in cached_frame.iterrows()
        }

        started = time.perf_counter()
        direct_map = {}
        for key, concept_id in keys.items():
            for index, (_label, s, e) in enumerate(WINDOWS):
                direct_map[(key, index)] = direct_prevalence(b, table, concept_id, s, e)
        direct = time.perf_counter() - started

        mismatches = [
            {"key": k, "cached": cached_map.get(k), "direct": v}
            for k, v in direct_map.items()
            if cached_map.get(k, 0) != v
        ]
        results.append(
            {
                "repeat": repeat,
                "features": len(specs),
                "windows": len(WINDOWS),
                "combinations": len(specs) * len(WINDOWS),
                "build_generated": len(built.generated),
                "cached_seconds": round(cached, 2),
                "direct_seconds": round(direct, 2),
                "speedup": round(direct / cached, 1) if cached else None,
                "mismatches": len(mismatches),
                "mismatch_sample": mismatches[:5],
            }
        )
        print(results[-1], flush=True)

    (OUT / "scale.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    section = sys.argv[1] if len(sys.argv) > 1 else "equivalence"
    {"equivalence": section_equivalence, "timing": section_timing, "scale": section_scale}[section]()
