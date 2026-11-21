# Era cache

`circe.era_cache` stores feature *events*, not realised covariates.

A covariate in FeatureExtraction is a value for a (cohort entry, time-at-risk
window) pair. That design is fine for one study but it throws information away:
a second study, a different TAR or an overlapping cohort has to re-scan the CDM.

The era cache keeps the underlying events instead:

```
era_feature_presence     (cache_key, feature_key, subject_id, era_start, era_end, concept_id)
era_feature_categorical  (... + value_concept_id, unit_concept_id)
era_feature_continuous   (... + value_num, unit_concept_id, range_low, range_high, operator_concept_id)
era_feature_registry     (feature_key, cache_key, completed, row_count, subject_count, ...)
```

Windows, time-at-risk settings and cohort membership are applied when reading.
That is what makes one build serve many studies.

## Identity

| Key | Contains | Excludes |
|---|---|---|
| `feature_key` | source table, concept set, value class, record filters | window, TAR, cohort, analysis id, display name |
| `cache_key` | CDM + vocabulary + engine fingerprints | feature identity |

A feature means the same thing after a vocabulary refresh, so `feature_key` does
not change; the rows that answer it belong to a generation, so `cache_key` does.
Regenerating after a data change writes a new generation rather than mixing
them.

## Feature classes

Three storage classes, because they are genuinely different kinds of variable:

| Class | Stored | Aggregations |
|---|---|---|
| presence | concept, era | exists, count, distinct count |
| categorical | concept + observed `value_as_concept_id` | exists, count, equality on the value concept |
| continuous | concept + `value_as_number`, unit, reference range | exists, count, mean, min, max, first, last |

`value_as_concept_id` is an observed OMOP concept supplied by the source system;
it is stored verbatim and never imputed. "Above normal range" is a **derived**
predicate (`value_num > range_high`) evaluated at read time, so different value
conditions can be answered from the same rows.

## Building

```python
from circe.era_cache import EraFeatureSpec, build_era_cache, EraCache

specs = [
    EraFeatureSpec(
        name="Type 2 diabetes",
        source_table="condition_occurrence",
        concept_ids=(201826,),
        include_descendants=True,
    ),
]
outcome = build_era_cache(
    specs,
    backend=backend,
    cache_schema="feature_cache",
    cdm_schema="cdm",
    vocabulary_schema="vocab",
)
outcome.summary()   # generated / reused / failed / rows
```

Builds are resumable. Concept sets are resolved once into a shared coding map,
each feature is written per family, and a feature is marked complete only after
its rows are durable. A failed feature is marked incomplete and does not block
the rest.

Pass `cdm_fingerprint` / `vocab_fingerprint` when the CDM or vocabulary changes;
otherwise the schema names are used and a refresh is not detected.

## Reading

```python
from circe.era_cache import CohortEraSpec, load_cohort, prevalence

cohort = load_cohort(backend.table("cohort", "results"), cohort_id=1)
result = prevalence(
    cohort,
    windows=[CohortEraSpec(-365, 0), CohortEraSpec(-90, 0)],
    backend=backend,
    cache_schema="feature_cache",
    observation_period=backend.table("observation_period", "cdm"),
)
# window_index, feature_key, numerator, denominator, prevalence
```

`CohortEraSpec` is the TAR: `start_days`/`end_days` relative to the index date,
clamped to the observation period. `start_days=None` means unbounded prior
history.

`feature_values()` returns `num_events`, `last_value`, `mean_value`, `min_value`
and `max_value`, optionally filtered by `predicate="above_normal"`,
`"below_normal"` or `"within_normal"`.

`feature_membership()` returns `(row_id, window_index, feature_key)` and spans
all three storage classes, so a caller can build its own aggregation.

## Validation

Parity against FeatureExtraction 3.14.0 on a Synthea OMOP CDM (465,428
persons; 58.1M condition rows):

- **42 of 42 comparisons matched exactly** across 4 cohorts x 2 windows x 6
  chronic conditions. No tolerance.
- Direct CDM queries matched the cached numerators exactly for the same
  cohorts and windows.

Performance on the same data:

| Scenario | Cached | Direct | Speedup |
|---|---:|---:|---:|
| warm rebuild | ~0.3 s | — | ~10x vs cold |
| 1 cohort, 6 features x 2 windows | 8.4–10.3 s | 16.3–17.2 s | 1.7–1.9x |
| 1 cohort, 20 features x 2 windows | 11.6–14.3 s | 55–125 s | 3.9–10.8x |

The single-feature case is close to neutral; the benefit comes from reuse.

## Backends

The cache compiles to ibis and runs on any supported backend. A
`ThriftBackend` adapter in `spark_backend.py` covers Spark Thrift Server, which
has no Spark Connect endpoint. It reconnects on dropped sessions, uses
`INSERT INTO ... SELECT` (ibis' generic insert becomes CTAS on Spark), and
issues `SET spark.sql.autoBroadcastJoinThreshold=-1` before touching the large
era tables so Spark does not try to broadcast millions of rows.

## Not yet covered

- Value features are tested on DuckDB only: the local Synthea CDM has no
  populated `value_as_number` or `value_as_concept_id`.
- Derived value predicates are read-time only; no materialised `feature_values`
  table yet.
- No table partitioning or indexing; reads scan the era table.
