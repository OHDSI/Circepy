# Event-level feature cache

This note evaluates the idea of caching feature results as
`(feature id, patient id, feature date)`, using PR 60's checksum-keyed cohort
cache as the model. It is a design note; no code changes are proposed here.

## Verdict

**Yes, it makes sense — as an event-level cache with a window-independent
feature key.** It is the right normalisation for reuse across target cohorts and
time windows.

**No, the three-column tuple is not sufficient as stated.** A feature is not
always a point event; features have intervals, values and index-relative
semantics, and a feature identity that includes the window defeats reuse. The
cache needs:

- `event_start_date` and `event_end_date` (not one date);
- a content-addressed `feature_key` that excludes window and aggregation;
- value/concept/unit columns for value features;
- a separate `feature_instance_key` for window + aggregation;
- a `population_key` for the target cohort/index date;
- a registry with completion, row count and data/vocabulary fingerprints.

With those adjustments, the idea is strong and fits both the cohort-first
extractor and the richer `circe.features` layer.

## What PR 60 does

PR 60 (open, `feature/decomposable-cohorts` → `develop`) adds a checksum-keyed
cohort cache in `circe/runner/cache.py`:

```text
cohort_cache (
    cohort_checksum, subject_id, cohort_start_date, cohort_end_date
)
cohort_cache_registry (
    cohort_checksum, completed, row_count, updated_at, completed_at
)
cohort_output_map (
    cohort_definition_id, cohort_checksum, row_count, completed, ...
)
```

The important design choices are:

1. **Content-addressed identity.** `cohort_checksum` is
   `semantic_expression_key(expression, include_title=False)`: concept-set ids
   are rewritten by content, display metadata and title are ignored. The cache
   is keyed by meaning, not by integer cohort id.
2. **Completion registry.** A cache entry is reused only when it is `completed`
   and its stored `row_count` matches the actual row count.
3. **Staging and publish.** Missing families are generated into a
   `__cache_stage_*` table, then copied into the cache in one join, then marked
   complete.
4. **Integer output is a projection.** The study-facing cohort table is written
   from the cache by joining `cohort_checksum` to integer cohort ids; an output
   map records what has been copied.
5. **Failure isolation.** A failed family is marked incomplete and does not
   block the rest.

This is an excellent template. The proposed feature cache is the same pattern at
a finer grain: events rather than cohort entries.

## Proposed cache

### Tables

```text
feature_event_cache (
    feature_key        VARCHAR,   -- content identity of the event selection
    subject_id         BIGINT,    -- person_id, not cohort row_id
    event_start_date   DATE,
    event_end_date     DATE,
    feature_kind       VARCHAR,   -- point | interval | cohort_entry
    concept_id         BIGINT,
    source_concept_id  BIGINT,
    value_num          DOUBLE,
    value_concept_id   BIGINT,
    unit_concept_id    BIGINT,
    event_id           BIGINT,    -- source row id or stable hash
    source_table       VARCHAR
)

feature_event_registry (
    feature_key        VARCHAR,
    feature_kind       VARCHAR,
    completed          BOOLEAN,
    row_count          BIGINT,
    cdm_fingerprint    VARCHAR,
    vocab_fingerprint  VARCHAR,
    engine_version     VARCHAR,
    updated_at         TIMESTAMP,
    completed_at       TIMESTAMP
)

feature_instance_cache (              -- optional, for expensive aggregations
    feature_instance_key VARCHAR,
    population_key       VARCHAR,
    row_id               BIGINT,
    value                DOUBLE
)

feature_output_map (                  -- integer feature ids for consumers
    feature_id    BIGINT,
    feature_key   VARCHAR,
    row_count     BIGINT,
    completed     BOOLEAN
)
```

### Identity

Do not use a single integer `feature_id` as the cache key. Define four levels:

| Key | Derived from | Changes when |
|---|---|---|
| `feature_key` | criterion/term + concept-set content + record filters + date adjustment + first flag | the event selection changes |
| `feature_instance_key` | `feature_key` + window + aggregation + grouping + time grid | a window or aggregation changes |
| `population_key` | target cohort definition/table + index date + row-id rule | the target population changes |
| `cache_key` | `feature_key` + CDM/vocab fingerprints + engine version | data or engine changes |

The integer `feature_id` is only an output mapping. If `feature_id` participates
in identity, two cohorts with different ids cannot share events.

For cohort features, `feature_key` is the cohort checksum
(`semantic_expression_key(include_title=False)`), and the cached rows are cohort
entries with `feature_kind = 'cohort_entry'`. That is exactly PR 60's
`cohort_cache`; the two can share a table or be unioned in a view.

### Why this enables window and cohort reuse

The cache stores **absolute event dates** and `subject_id`; the target cohort
supplies `(subject_id, index_date)` at query time. A window is a range
predicate, not part of the cache key:

```sql
-- exists in a -365..0 window
SELECT DISTINCT c.subject_id
FROM feature_event_cache c
JOIN target t ON t.subject_id = c.subject_id
WHERE c.feature_key = :feature_key
  AND c.event_start_date BETWEEN t.index_date - 365 AND t.index_date;
```

The same rows answer:

- `exists` in any window;
- `count` and `distinct_count`;
- `first` / `last` and time-to-event;
- interval overlap (`start <= upper AND end >= lower`);
- sequence/gap features;
- cohort membership at a different index date.

Only the read query changes; the cache is built once.

## What the tuple misses

1. **Intervals.** Drug eras, condition eras, visits and cohort entries have
   start and end dates. One `feature_date` cannot answer overlap semantics.
2. **Values.** Measurement/observation value features need
   `value_num`/`value_concept_id`/`unit_concept_id`; otherwise only
   existence/count are supported.
3. **Multiple events per person/date.** `(feature, patient, date)` is not unique.
   Add `event_id`/`source_id`, or define dedup semantics per feature kind.
4. **Index-relative features.** Age, prior observation time, cohort membership,
   "first event after index", sequence state and time-in-cohort cannot be
   derived from a person-level event cache alone. They need a separate
   `derived`/`population` cache keyed by `population_key`.
5. **`first=True` semantics.** "First event per person in the source" is
   index-independent and can be cached; "first event in the window" is
   index-dependent and must be computed at query time. Store an `is_first` flag
   or all events.
6. **Observation periods and follow-up.** Cache events as extracted; apply the
   target cohort's observation period, washout and censorship at query time.
7. **Data/vocabulary drift.** PR 60 checks row count, which detects truncation
   but not updates. Add `cdm_fingerprint`, `vocab_fingerprint` and
   `engine_version` to the registry.
8. **Negative/zero events.** Keep the cache sparse; derive zeros by anti-join or
   cross join at matrix time.

## Fit with the current code

`circe/cohort_features` currently:

- converts every feature to a `CohortDefinitionSet`;
- calls `generate_cohort_set(..., shared=True)` into `feature_cohort`;
- applies the feature window when building the matrix;
- keys output by integer `feature_id`;
- regenerates on each call.

This is already close to the proposed model: feature cohorts are generated
window-free and windows are applied at query time. What is missing is the cache
discipline:

- identical feature definitions with different integer ids duplicate work;
- there is no completion registry or partial-failure protection;
- there is no content-addressed key (`CohortFeature.checksum()` uses
  `CohortExpression.checksum()`, which is not the canonical
  `semantic_expression_key(include_title=False)`);
- there is no data/vocabulary fingerprint.

Adapting PR 60 would fix the first three. The event cache would additionally
support value features and arbitrary windows without re-running cohort
generation.

`circe.features` (the parallel layer) already plans an event-spine cache with
`feature_values`; the two should share the same `feature_key`/instance/population
contract rather than inventing different keys.

## Plan

### Phase 0 — settle the contract

- Define `feature_key`, `feature_instance_key`, `population_key`, `cache_key`.
- Decide between one unified `feature_event_cache` and separate
  `cohort_cache` (PR 60) + `event_cache` tables.
- Add `feature_kind`, `event_start_date`, `event_end_date`, value columns.
- Add `cdm_fingerprint` and `vocab_fingerprint` to the registry.
- Write tests for key stability and for the "same events, different window"
  invariant.

### Phase 1 — checksum-keyed cohort-feature cache

Lowest-risk, immediate win:

1. Port PR 60's `CohortCache`, registry, staging and output map into
   `circe/cohort_features` (or a small shared `circe/feature_cache` module).
2. Use `cohort_checksum`/`semantic_expression_key(include_title=False)` as the
   feature key for `CohortFeature`.
3. Generate missing feature cohorts into staging; publish by `feature_key`.
4. Maintain `feature_output_map` from integer `feature_id` to `feature_key`.
5. Make `extract_feature_matrix` read cached cohort rows and apply windows.
6. Reuse across runs, feature sets and target cohorts; dedupe identical
   definitions.

Exit criteria: two feature sets with different ids but identical definitions
share rows; a failed build leaves no reusable partial entry; a second run
performs zero generation when all keys are complete.

### Phase 2 — event cache for criteria/value features

1. For `CriteriaFeature`, generate canonical events rather than only cohort
   rows (reuse `compile_event_plan` / the execution engine).
2. Store `(feature_key, subject_id, event_start, event_end, concept_id,
   value...)`.
3. Derive windows and aggregations at query time.
4. Support `exists`, `count`, `distinct_count`, `first`, `last`, `value`.
5. Add `feature_event_registry` with row counts and fingerprints.
6. Add a `feature_instance_cache` only for expensive aggregations or repeated
   matrix builds.

Exit criteria: one event cache serves at least three windows and two target
cohorts; results match uncached extraction; value features round-trip.

### Phase 3 — scale and operations

- Partition/cluster `feature_event_cache` by `feature_key` and date; index
  `(feature_key, subject_id, event_start_date)`.
- Cache selectively: high-reuse/high-cost features only; low-reuse features
  stay on demand.
- Add retention/GC for stale or incomplete entries.
- Add concurrency control (unique key or registry lock).
- Benchmark storage vs compute at realistic CDM sizes; report hit rate and
  speedup.
- Reuse the stale-session registry for staging cleanup.

### Phase 4 — shared contract with `circe.features`

- Align `feature_key` with `term_key`/`concept_set_key` from `circe.features`.
- Let `circe.features` read the event cache for its term events.
- Let `circe.cohort_features` read the same cache for cohort-as-feature.
- Ensure one cache can feed Characterization, ML and PLE without duplication.

## Does it make sense?

**Yes, for event-selected features.** It is the correct grain for reuse: a
target cohort is a lens on person-level events, and a window is a predicate.
Caching `(feature_key, subject_id, start, end, values)` lets one build serve many
cohorts and windows.

**No, not as a universal three-column key.** It fails for intervals, values,
multiple events per day, index-relative features and data drift. It also fails
if `feature id` includes the window or aggregation, because then nothing is
shared.

**Recommendation:** use PR 60's pattern, but split identity into
`feature_key` (cache) and `feature_instance_key` (window/aggregation), store
intervals and values, and add fingerprints to the registry. Start with Phase 1
(cohort-feature cache) because it is a direct adaptation of PR 60 and delivers
dedupe/reuse immediately; add Phase 2 when value/sequence features are needed.

## References

- PR 60 — https://github.com/OHDSI/Circepy/pull/60
- PR 60 cache implementation — `circe/runner/cache.py`
- PR 60 cache migration note — `docs/developer/cohort-cache-migration.md`
- PR 60 canonical checksum — `circe/decomposition/canonical.py`
- Current cohort-first extractor — `circe/cohort_features/extract.py`
