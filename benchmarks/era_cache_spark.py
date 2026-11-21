"""Demonstrable equivalence and speed: cached reads vs direct CDM queries.

The script answers two questions against the live local Spark CDM:

1. **Equivalence** — for several cohorts and several time-at-risk windows, does
   a prevalence ratio computed from the era cache equal the same ratio computed
   directly from the CDM?
2. **Speed** — what does a first run cost, and what does a repeated run on the
   same population cost once the cache exists?

The direct baseline is deliberately the *same definition* the cache stores
(concept set, era bounds, observation-period rules), so any difference is a bug
rather than a modelling choice.

Output is written as JSON so a report can be rendered from it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from circe.era_cache import (
    CohortEraSpec,
    EraFeatureSpec,
    era_feature_key,
    load_cohort,
    prevalence,
)
from circe.era_cache.spark_backend import ThriftBackend

# Chronic-condition features used for every cohort.  Concept ids are standard
# OMOP SNOMED concepts present in the Synthea vocabulary.
FEATURES = {
    "Type 2 diabetes": (201826,),
    "Heart failure": (316139,),
    "Obesity": (433736,),
    "Asthma": (317009,),
    "Chronic kidney disease": (46271022,),
    "Chronic obstructive pulmonary disease": (255573,),
}

WINDOWS = [("1 year prior", -365, 0), ("90 days prior", -90, 0), ("all prior", None, 0)]


@dataclass(frozen=True)
class CohortSpec:
    name: str
    concept_id: int


COHORTS = [
    CohortSpec("first type 2 diabetes", 201826),
    CohortSpec("first obesity", 433736),
    CohortSpec("first chronic kidney disease", 46271022),
    CohortSpec("first asthma", 317009),
]


def top_condition_concepts(backend: ThriftBackend, *, cdm_schema: str, limit: int) -> list[int]:
    """Return the most frequent standard condition concepts in the CDM."""
    frame = backend.execute_raw(
        f"SELECT condition_concept_id, COUNT(*) AS n FROM {cdm_schema}.condition_occurrence "
        "WHERE condition_concept_id > 0 GROUP BY condition_concept_id "
        f"ORDER BY n DESC LIMIT {int(limit)}"
    )
    return [int(value) for value in frame["condition_concept_id"].tolist()]


def scale_features(backend: ThriftBackend, *, cdm_schema: str, count: int) -> list[EraFeatureSpec]:
    """Build ``count`` single-concept condition features from real concepts."""
    concepts = top_condition_concepts(backend, cdm_schema=cdm_schema, limit=count)
    return [
        EraFeatureSpec(
            name=f"condition_{concept_id}",
            source_table="condition_occurrence",
            concept_ids=(concept_id,),
        )
        for concept_id in concepts
    ]


def specs() -> list[EraFeatureSpec]:
    return [
        EraFeatureSpec(
            name=name,
            source_table="condition_occurrence",
            concept_ids=concept_ids,
        )
        for name, concept_ids in FEATURES.items()
    ]


def ensure_cache(backend: ThriftBackend, *, cache_schema: str, cdm_schema: str, vocab_schema: str):
    from circe.era_cache import build_era_cache

    started = time.perf_counter()
    outcome = build_era_cache(
        specs(),
        backend=backend,
        cache_schema=cache_schema,
        cdm_schema=cdm_schema,
        vocabulary_schema=vocab_schema,
    )
    elapsed = time.perf_counter() - started
    return outcome, elapsed


def make_cohort(
    backend: ThriftBackend,
    *,
    cache_schema: str,
    cohort: CohortSpec,
    start_year: int = 2008,
    end_year: int = 2009,
) -> str:
    """First occurrence of a condition inside a window, with one year of follow-up."""
    import uuid

    table = f"cohort_{cohort.concept_id}_{uuid.uuid4().hex[:6]}"
    key = era_feature_key(
        EraFeatureSpec(
            name=cohort.name,
            source_table="condition_occurrence",
            concept_ids=(cohort.concept_id,),
        )
    )
    backend.raw_sql(f"DROP TABLE IF EXISTS {cache_schema}.{table}")
    backend.raw_sql(
        f"CREATE TABLE {cache_schema}.{table} USING DELTA AS "
        "SELECT 1 AS cohort_definition_id, t.subject_id, t.first_date AS cohort_start_date, "
        "DATE_ADD(t.first_date, 365) AS cohort_end_date FROM ("
        f"SELECT e.subject_id, MIN(e.era_start) AS first_date "
        f"FROM {cache_schema}.era_feature_presence e "
        f"WHERE e.feature_key = '{key}' GROUP BY e.subject_id) t "
        f"WHERE t.first_date >= DATE'{start_year}-01-01' "
        f"AND t.first_date <= DATE'{end_year}-12-31'"
    )
    return table


def direct_prevalence(
    backend: ThriftBackend,
    *,
    cdm_schema: str,
    cache_schema: str,
    cohort_table: str,
    concept_id: int,
    start_days: int | None,
    end_days: int,
) -> tuple[int, int]:
    """Compute prevalence straight from the CDM in one SQL statement."""
    lower = "c.cohort_start_date" if start_days is None else f"DATE_ADD(c.cohort_start_date, {start_days})"
    upper = f"DATE_ADD(c.cohort_start_date, {end_days})"
    sql = f"""
    SELECT COUNT(DISTINCT c.subject_id) AS numerator,
           (SELECT COUNT(DISTINCT subject_id)
              FROM {cache_schema}.{cohort_table}) AS denominator
    FROM {cache_schema}.{cohort_table} c
    JOIN {cdm_schema}.observation_period op
      ON op.person_id = c.subject_id
     AND c.cohort_start_date BETWEEN op.observation_period_start_date
                                 AND op.observation_period_end_date
    JOIN {cdm_schema}.condition_occurrence co
      ON co.person_id = c.subject_id
     AND co.condition_concept_id = {concept_id}
    WHERE co.condition_start_date <= LEAST({upper}, op.observation_period_end_date)
      AND COALESCE(co.condition_end_date, co.condition_start_date)
          >= GREATEST({lower}, op.observation_period_start_date)
    """
    frame = backend.execute_raw(sql)
    return int(frame.iloc[0]["numerator"]), int(frame.iloc[0]["denominator"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--cdm-schema", default="cdm")
    parser.add_argument("--vocab-schema", default="vocab")
    parser.add_argument("--cache-schema", default="cdm_era_cache")
    parser.add_argument("--output", default="benchmarks/feature_parity/results.json")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--skip-cohorts", action="store_true")
    parser.add_argument("--scale-features", type=int, default=40)
    parser.add_argument(
        "--sections",
        default="equivalence,timing,scale",
        help="comma separated subset of: equivalence,timing,scale",
    )
    args = parser.parse_args(argv)

    backend = ThriftBackend(host=args.host, port=args.port)
    from circe.era_cache.schema import LARGE_TABLES

    backend.no_broadcast_tables.update(LARGE_TABLES)
    for table_name in backend.execute_raw(f"SHOW TABLES IN {args.cache_schema}")["tableName"].tolist():
        if table_name.startswith(("cohort_", "demo_cohort")):
            backend.raw_sql(f"DROP TABLE IF EXISTS {args.cache_schema}.`{table_name}`")
    result: dict[str, object] = {"features": list(FEATURES), "windows": WINDOWS, "cohorts": []}

    # -- first build (cold) -------------------------------------------------
    outcome, build_seconds = ensure_cache(
        backend,
        cache_schema=args.cache_schema,
        cdm_schema=args.cdm_schema,
        vocab_schema=args.vocab_schema,
    )
    result["cold_build"] = {
        "seconds": round(build_seconds, 2),
        "generated": len(outcome.generated),
        "reused": len(outcome.reused),
        "failed": outcome.failed,
        "rows": sum(outcome.row_counts.values()),
    }

    # -- repeated build (warm) ---------------------------------------------
    warm_times = []
    for _ in range(args.repeats):
        _, seconds = ensure_cache(
            backend,
            cache_schema=args.cache_schema,
            cdm_schema=args.cdm_schema,
            vocab_schema=args.vocab_schema,
        )
        warm_times.append(round(seconds, 2))
    result["warm_build"] = {
        "seconds": warm_times,
        "mean_seconds": round(sum(warm_times) / len(warm_times), 3),
        "speedup_vs_cold": round(build_seconds / (sum(warm_times) / len(warm_times)), 1),
    }

    key_to_name = {era_feature_key(spec): spec.name for spec in specs()}
    observation_period = backend.table("observation_period", args.cdm_schema)

    for cohort in COHORTS:
        cohort_table = make_cohort(backend, cache_schema=args.cache_schema, cohort=cohort)
        relation = load_cohort(backend.table(cohort_table, args.cache_schema), cohort_id=1)
        size = int(backend.execute(relation.count()).iloc[0, 0])
        entry: dict[str, object] = {"cohort": cohort.name, "size": size, "windows": []}

        for label, start_days, end_days in WINDOWS:
            # cached
            cached_started = time.perf_counter()
            frame = backend.execute(
                prevalence(
                    relation,
                    windows=[CohortEraSpec(start_days, end_days)],
                    backend=backend,
                    cache_schema=args.cache_schema,
                    observation_period=observation_period,
                )
            )
            cached_seconds = time.perf_counter() - cached_started
            frame["name"] = frame["feature_key"].map(key_to_name)
            cached = {
                row["name"]: (int(row["numerator"]), int(row["denominator"])) for _, row in frame.iterrows()
            }

            # direct
            direct_started = time.perf_counter()
            direct = {}
            for name, concept_ids in FEATURES.items():
                direct[name] = direct_prevalence(
                    backend,
                    cdm_schema=args.cdm_schema,
                    cache_schema=args.cache_schema,
                    cohort_table=cohort_table,
                    concept_id=concept_ids[0],
                    start_days=start_days,
                    end_days=end_days,
                )
            direct_seconds = time.perf_counter() - direct_started

            comparisons = []
            for name in FEATURES:
                cached_num, cached_den = cached.get(name, (0, size))
                direct_num, direct_den = direct[name]
                comparisons.append(
                    {
                        "feature": name,
                        "cached_numerator": cached_num,
                        "direct_numerator": direct_num,
                        "denominator_cached": cached_den,
                        "denominator_direct": direct_den,
                        "cached_prevalence": round(cached_num / size, 6) if size else 0.0,
                        "direct_prevalence": round(direct_num / size, 6) if size else 0.0,
                        "equal": cached_num == direct_num and cached_den == direct_den,
                    }
                )

            entry["windows"].append(
                {
                    "window": label,
                    "start_days": start_days,
                    "end_days": end_days,
                    "cached_seconds": round(cached_seconds, 2),
                    "direct_seconds": round(direct_seconds, 2),
                    "speedup": round(direct_seconds / cached_seconds, 2) if cached_seconds > 0 else None,
                    "all_equal": all(item["equal"] for item in comparisons),
                    "comparisons": comparisons,
                }
            )
        result["cohorts"].append(entry)

    # -- many-feature / many-window scenario --------------------------------
    # One build serves N features x M windows.  The direct baseline runs
    # N x M statements; the cache runs one build plus one read per cohort.
    scale_specs = scale_features(backend, cdm_schema=args.cdm_schema, count=args.scale_features)
    from circe.era_cache import build_era_cache
    from circe.era_cache import era_feature_key as _key

    scale_started = time.perf_counter()
    scale_outcome = build_era_cache(
        scale_specs,
        backend=backend,
        cache_schema=args.cache_schema,
        cdm_schema=args.cdm_schema,
        vocabulary_schema=args.vocab_schema,
    )
    scale_build_seconds = time.perf_counter() - scale_started

    scale_windows = [CohortEraSpec(start, end) for _label, start, end in WINDOWS]
    scale_cohort = COHORTS[0]
    scale_table = make_cohort(backend, cache_schema=args.cache_schema, cohort=scale_cohort)
    scale_relation = load_cohort(backend.table(scale_table, args.cache_schema), cohort_id=1)

    cached_started = time.perf_counter()
    scale_frame = backend.execute(
        prevalence(
            scale_relation,
            windows=scale_windows,
            backend=backend,
            cache_schema=args.cache_schema,
            observation_period=observation_period,
        )
    )
    cached_scale_seconds = time.perf_counter() - cached_started

    direct_started = time.perf_counter()
    direct_rows = []
    for spec in scale_specs:
        for _label, start_days, end_days in WINDOWS:
            numerator, _denominator = direct_prevalence(
                backend,
                cdm_schema=args.cdm_schema,
                cache_schema=args.cache_schema,
                cohort_table=scale_table,
                concept_id=spec.concept_ids[0],
                start_days=start_days,
                end_days=end_days,
            )
            direct_rows.append({"feature_key": _key(spec), "start": start_days, "numerator": numerator})
    direct_scale_seconds = time.perf_counter() - direct_started

    direct_index = {(row["feature_key"], row["start"]): row["numerator"] for row in direct_rows}
    cached_index = {
        (row["feature_key"], WINDOWS[int(row["window_index"])][1]): int(row["numerator"])
        for _, row in scale_frame.iterrows()
    }
    mismatches = []
    for key, expected in direct_index.items():
        actual = cached_index.get(key)
        if actual is None or actual != expected:
            mismatches.append(
                {
                    "feature_key": key[0],
                    "start": key[1],
                    "cached": actual,
                    "direct": expected,
                }
            )
    missing_from_direct = [key for key in cached_index if key not in direct_index]

    result["scale_scenario"] = {
        "features": len(scale_specs),
        "windows": len(WINDOWS),
        "cohort": scale_cohort.name,
        "cohort_size": int(backend.execute(scale_relation.count()).iloc[0, 0]),
        "build_generated": len(scale_outcome.generated),
        "build_reused": len(scale_outcome.reused),
        "build_failed": scale_outcome.failed,
        "build_seconds": round(scale_build_seconds, 2),
        "cached_read_seconds": round(cached_scale_seconds, 2),
        "direct_read_seconds": round(direct_scale_seconds, 2),
        "cached_read_speedup": round(direct_scale_seconds / cached_scale_seconds, 1)
        if cached_scale_seconds > 0
        else None,
        "combinations": len(scale_specs) * len(WINDOWS),
        "mismatches": mismatches[:20],
        "missing_from_direct": missing_from_direct[:20],
        "all_equal": not mismatches,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))
    print(
        json.dumps(
            {
                "cold_build_seconds": result["cold_build"]["seconds"],
                "warm_build_mean_seconds": result["warm_build"]["mean_seconds"],
                "cohorts": len(result["cohorts"]),
                "scale_all_equal": result["scale_scenario"]["all_equal"],
                "scale_combinations": result["scale_scenario"]["combinations"],
                "scale_cached_seconds": result["scale_scenario"]["cached_read_seconds"],
                "scale_direct_seconds": result["scale_scenario"]["direct_read_seconds"],
                "scale_speedup": result["scale_scenario"]["cached_read_speedup"],
                "all_equal": all(
                    window["all_equal"] for cohort in result["cohorts"] for window in cohort["windows"]
                ),
                "output": str(output),
            },
            indent=2,
        )
    )
    backend.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
