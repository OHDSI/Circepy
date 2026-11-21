# Implementation plan: era-level feature cache with FeatureExtraction prevalence parity

Status: plan only. No implementation in this document.

## 1. Goal

Build a **CDM-wide, era-grain feature cache** on the `feature/feature-extraction`
branch, then validate it by comparing **feature prevalence** against OHDSI
FeatureExtraction on synthetic data.

Parity target is explicitly *rough*, not byte-identical:

- the same cohort entries and the same analysis family definitions;
- prevalence (`mean` over cohort entries) within a tolerance;
- differences explained, not hidden.

The cache stores each feature as an era and never realises it against a
time-at-risk window or cohort. Windows, TARs and cohort set operations are read
time predicates. This is what lets many TARs and many overlapping cohorts reuse
one build.

## 2. Decisions already made (from the design discussion)

| # | Decision |
|---|---|
| D1 | Cache grain is the **era**: `(feature_key, subject_id, era_start, era_end)`. |
| D2 | **No window, no TAR, no index date** in the cache. |
| D3 | `feature_key` is a content hash of the event selection only. |
| D4 | Three storage classes: **presence**, **categorical value**, **continuous value**. |
| D5 | `value_as_concept_id` is an **observed standard concept**, stored verbatim, never imputed. |
| D6 | "Above normal range" is a **derived predicate** (`value_num > range_high`), computed at read time. |
| D7 | Registry carries completion, row count, CDM/vocabulary fingerprints and engine version. |
| D8 | Build in staging, publish once, write per family so long runs are resumable. |

## 3. Repository layout

Everything is additive; existing `circe/features` (the other agent's work) and
`circe/cohort_features` are not modified.

```text
circe/era_cache/
    __init__.py
    keys.py            # feature_key derivation (content hashing)
    specs.py           # FeatureEraSpec: presence/categorical/continuous
    schema.py          # table DDL + shared column contracts
    registry.py        # completion, row counts, fingerprints
    build.py           # extract eras from CDM into staging, publish
    population.py      # target cohort -> (subject_id, index_date) relation
    read.py            # window predicates + aggregations over the cache
    parity.py          # legacy analysis catalogue (analysis_id <-> spec)
    fe_runner.py       # FeatureExtraction parity helpers (invoked by R script)
    cli.py             # `python -m circe.era_cache ...`
tests/era_cache/
    conftest.py        # synthetic CDM + vocabulary fixtures
    test_keys.py
    test_schema.py
    test_build.py
    test_read.py
    test_value_features.py
    test_registry.py
    test_windows_and_tars.py
    test_parity_catalogue.py
benchmarks/feature_parity/
    make_synthetic_cdm.py
    run_feature_extraction.R
    compare_parity.py
    README.md
docs/design/
    era-cache.md
```

## 4. Data model

### 4.1 Tables

```text
era_feature_categorical (
    cache_key        TEXT,     -- registry key (CDM/vocab/engine)
    feature_key      TEXT,     -- content hash of the event selection
    subject_id       BIGINT,
    era_start        DATE,
    era_end          DATE,
    concept_id       BIGINT,   -- standard concept that matched
    value_concept_id BIGINT,   -- observed standard concept result
    unit_concept_id  BIGINT,
    source_concept_id BIGINT,
    source_table     TEXT
)

era_feature_continuous (
    cache_key        TEXT,
    feature_key      TEXT,
    subject_id       BIGINT,
    era_start        DATE,
    era_end          DATE,
    concept_id       BIGINT,
    value_num        DOUBLE,
    unit_concept_id  BIGINT,
    range_low        DOUBLE,
    range_high       DOUBLE,
    operator_concept_id BIGINT,
    source_concept_id BIGINT,
    source_table     TEXT
)

era_feature_registry (
    feature_key      TEXT,
    cache_key        TEXT,
    family           TEXT,     -- domain family, e.g. condition_occurrence
    feature_kind     TEXT,     -- presence | categorical | continuous
    completed        BOOLEAN,
    row_count        BIGINT,
    subject_count    BIGINT,
    cdm_fingerprint  TEXT,
    vocab_fingerprint TEXT,
    engine_version   TEXT,
    updated_at       TIMESTAMP,
    completed_at     TIMESTAMP
)
```

Optional read-model tables, written only when materialisation is requested:

```text
era_feature_value (          -- realised (feature, cohort, row, window) values
    feature_key, cohort_definition_id, row_id, feature_id, value
)
```

`era_feature_value` is a **view of the cache under a window**, never the source
of truth.

### 4.2 Why two tables

- A categorical row never needs `value_num`, `range_low`, `range_high`,
  `operator_concept_id`.
- A continuous row never needs `value_concept_id`.
- Presence-only features live in the categorical table with
  `value_concept_id = NULL`; no third table is required.

This makes the valid aggregation set explicit: categorical supports
`exists`/`count`/`distinct_count` and equality on `value_concept_id`;
continuous supports `exists`/`count`, `mean`/`min`/`max`/`median`, and numeric
predicates.

### 4.3 `feature_key`

```
feature_key = sha256({
    "kind": "presence" | "categorical" | "continuous",
    "domain": "condition_occurrence" | ...,
    "concept_set": canonical_concept_set_content,
    "record_filters": {...},        # type/status/unit/route/visit filters
    "source_concepts": bool,        # whether source-concept matching is on
    "value_concept": concept_id?,   # categorical only
    "value_predicate": {...},       # continuous only: op, threshold, unit
    "interval_semantics": "point" | "interval"
})
```

Excluded from the key:

- analysis id, covariate id, display name, cohort id, index date, TAR, window;
- concept-set local ids and display metadata (reuse
  `concept_set_content_key` / `semantic_expression_key` from
  `circe/decomposition/canonical.py`).

Result: the same event selection produces the same key across cohorts, feature
sets and runs.

## 5. Extraction

For each feature spec:

1. Resolve the concept set once per build into `(codeset_id, concept_id)`
   (reuse `build_feature_codeset_table` logic).
2. Emit an era relation per family:
   - `condition_occurrence` → `(condition_start_date, COALESCE(condition_end_date, condition_start_date))`
   - `drug_exposure` → `(drug_exposure_start_date, COALESCE(drug_exposure_end_date, start + days_supply))`
   - `condition_era` / `drug_era` / `dose_era` → era start/end
   - `measurement` / `observation` → `(date, date)` plus value columns
   - `visit_occurrence` / `visit_detail` → start/end
   - `procedure_occurrence` / `device_exposure` / `specimen` → date
3. Deduplicate to one row per `(feature_key, subject_id, era_start, era_end,
   [value columns])`.
4. Union across the family, write into a staging table, record counts, mark
   complete.

All extraction is lazy ibis; only counts cross into Python.

### 5.1 Batch / family strategy

- Group features by **source table** and **concept-set shape** so one domain scan
  serves many features where possible.
- v1 may emit one CTAS per feature for correctness; batching is an optimisation
  with a parity test that they produce the same rows.
- Write and mark complete **per family** so a 2h run costs at most one family.

## 6. Read API

```python
EraCache(backend, schema="feature_cache")
  .build(specs, cdm_schema=..., vocabulary_schema=..., families=[...])
  .explain()                                   # what is cached, what is missing
  .eras(feature_key)                           # lazy era relation
  .matrix(cohort, index="cohort_start_date", windows=[..., ...],
          aggregations=["exists", "count"])    # lazy (row_id, feature_id, value)
  .prevalence(cohort, window, aggregation)     # lazy per-feature mean
```

### 6.1 Window predicates

- `basis="start"`: `era_start BETWEEN index+start AND index+end`
- `basis="end"`: `era_end BETWEEN ...`
- `overlap=True`: `era_start <= index+end AND era_end >= index+start`

These are the three semantics FeatureExtraction uses across its SQL templates.

### 6.2 Derived value features

- continuous: `value_num > range_high`, `< range_low`, `BETWEEN`, threshold on
  `unit_concept_id`;
- null `value_num` never matches a numeric predicate (documented, not imputed);
- censored values (`operator_concept_id` set) are included as-is; comparison of
  a censored value is documented as approximate.

### 6.3 Observation period handling

The cache stores eras **unfiltered by target observation periods**. Read time
joins the target cohort and applies the observation-period/eligibility rule the
caller requests. This must be explicit, otherwise events outside follow-up leak
into prevalence.

## 7. FeatureExtraction parity plan

### 7.1 What "rough parity" means

For each comparable feature and each cohort:

```
prevalence_mine = count(distinct row_id with feature in window) / count(row_id)
prevalence_fe   = sumValue / averageValue->populationSize  (FE aggregated output)
```

Acceptance (initial):

- binary presence features: absolute difference ≤ 0.02, or relative ≤ 20% when
  prevalence < 0.02;
- continuous features: mean difference within 5% or 0.1 SD;
- count features: mean difference within 10%;
- any feature with a larger gap must be listed in a documented **known-divergence
  table** with a reason.

A hard secondary check: for features with identical concept sets and windows,
row sets should match exactly; sample 20 features and assert exact equality.

### 7.2 Environment

- Run FeatureExtraction in its **native R + Java + DatabaseConnector** stack.
- Target database: **PostgreSQL/DuckDB file shared between R and Python**, or
  run R against DuckDB via the DuckDB JDBC driver. A shared DuckDB file is
  preferred because both sides read the identical CDM.
- Pin: FeatureExtraction version, R version, Java version, DatabaseConnector,
  SqlRender, vocabulary release, Synthea export.

### 7.3 Synthetic CDM generator

`benchmarks/feature_parity/make_synthetic_cdm.py`

1. Generate a Synthea CSV export (Synthea 3.x, seeded, `-p` patients,
   `exporter.csv.export=true`), **or** reuse an existing export.
2. Load it to a DuckDB OMOP CDM (v5.4) using the ETL-Synthea SQL mapping
   (a small Python port for the tables we need), or accept a prebuilt CDM file
   produced by ETL-Synthea/PostgreSQL and copy it to DuckDB via `duckdb`
   `ATTACH` + `CREATE TABLE AS`.
3. Load vocabulary tables (`concept`, `concept_ancestor`,
   `concept_relationship`, `concept_class`, `domain`, `vocabulary`,
   `relationship`) from an Athena bundle (path provided via env var).
4. Build the target cohort exactly as FeatureExtraction's unit-test cohort
   (first drug use, ≥365 days prior observation), plus 2–3 extra cohorts with
   different index dates to exercise TAR reuse.
5. Write `manifest.json` with seeds, versions and row counts.

Fallback if Synthea is unavailable: a seeded synthetic generator that writes the
CDM tables directly with realistic concept distributions (a small vocabulary
subset with ancestors). This keeps CI hermetic; the Synthea run is the
realistic check.

### 7.4 Feature set under test

Start with the prespecified analyses that map cleanly to eras:

| FE analysis family | My spec |
|---|---|
| Demographics (age, gender, race, year/month) | population/derived, not era cache |
| Condition occurrence (any time prior / long / short term) | presence, windows on `condition_start_date` |
| Condition era / condition group era | presence, overlap windows |
| Drug exposure / drug era / drug group era | presence, overlap windows |
| Procedure / device | presence |
| Measurement (presence) | presence |
| MeasurementValue (any time prior / long / short term) | continuous, `mean`/`last` |
| MeasurementRangeGroup (above/within/below normal) | continuous derived predicates |
| MeasurementValueAsConcept | categorical (`value_concept_id`) |
| Observation / ObservationValue / ObservationValueAsConcept | presence / continuous / categorical |
| Concept counts (distinct condition/ingredient/procedure/measurement/observation counts) | continuous count aggregations |
| Visit counts / visit concept counts | presence + count |

Out of scope for v1 parity: temporal sequences, scores (Charlson etc.), cohort
as covariate, care site, HDPS, notes.

### 7.5 Harness

`benchmarks/feature_parity/run_feature_extraction.R`

- reads `manifest.json` (CDM path, cohort id, output path);
- calls `FeatureExtraction::getDbCovariateData(aggregated = TRUE,
  rowIdField = "subject_id")` with `createDefaultCovariateSettings()` and a
  detailed settings object limited to the analyses under test;
- writes `covariateRef`, `analysisRef`, `covariates` (aggregated) as CSVs.

`benchmarks/feature_parity/compare_parity.py`

- maps FE `analysisId` → my `feature_key` via
  `circe/era_cache/parity.py` (a data table, versioned);
- computes prevalence on both sides over the same cohort and TAR;
- emits `parity_report.md` + `parity.csv` with per-feature differences,
  pass/fail and the known-divergence list;
- fails CI above tolerance.

### 7.6 TAR reuse check

Build the cache **once**, then compute prevalence for:

- cohort A with TAR `[-365, 0]`;
- cohort A with TAR `[-30, 0]`;
- cohort B (different index date) with both TARs.

Assert: one build, four reads, no cache regeneration, and each read matches
the corresponding FE run (or is listed as a known divergence). This is the
property the era cache exists to provide.

### 7.7 Known divergences to document up front

- Implicit observation-period handling differs between FE templates.
- Date adjacencies: FE uses `DATEADD(DAY, n, ...)`; mapping to interval
  boundaries must be checked on leap days and month ends.
- `condition_end_date` null handling (`start + 1 day` vs `start`).
- Drug era vs drug exposure duration for `days_supply` nulls.
- FE's `distinct` vs `count` for repeated same-day events.
- `value_as_concept_id = 0` treated as unknown, not as a concept.
- Post-coordinated measurement values (FE packs value/unit into a concept).
- FE's `endDays = 0` window includes the index day; my `[start, end]` is closed.

## 8. Testing strategy

### 8.1 Unit (DuckDB, deterministic)

- **Key stability**: same concept set with different ids/titles → same key;
  different window/aggregation → same key (window is not in the key); different
  concept set → different key.
- **Schema**: categorical rows carry no continuous columns and vice versa;
  presence rows have null value columns.
- **Value features**: null values excluded from numeric predicates;
  `above_normal` / `below_normal` / `within` computed correctly; censored values
  handled as documented; unit-filtered features.
- **Eras**: interval features keep start/end; point features use equal dates;
  duplicate rows deduplicated.
- **Windows**: start-basis, end-basis and overlap semantics; `[−365, 0]` and
  `[−30, 0]` return the expected row sets.
- **Observation period**: events outside follow-up are excluded at read time.
- **Registry**: incomplete entries are never reused; row-count drift invalidates;
  fingerprints change the cache key; failed build leaves no complete entry.
- **Idempotency**: second build with everything complete does zero
  extraction (assert via query counts or a mocked extractor).
- **Materialisation**: `era_feature_value` matches a direct read.

### 8.2 Integration (synthetic CDM)

- Build 40–60 features across condition/drug/measurement/observation/procedure
  against the seeded CDM.
- Assert known prevalence values computed by hand on a small fixture.
- Assert one build serves multiple cohorts and TARs identically.
- Assert `explain()` reports the expected hit/miss counts.

### 8.3 Parity (R + FeatureExtraction)

- Runs nightly/manual, not on every PR (R/Java/Athena dependency).
- Seeded Synthea CDM committed as a manifest (not the data); CI job builds from
  the seed.
- Tolerance gates as in §7.1.
- Golden file `parity_report.md` committed and diffed.

### 8.4 Regression and CI gates

- `pytest tests/era_cache` in the standard suite (DuckDB only).
- Existing pre-commit ruff checks.
- A `--only parity` mode in `scripts/ci_preflight.py` is **not** added; parity
  stays a separate workflow because it needs R, Java and vocabulary assets.

## 9. Milestones

| M | Deliverable | Exit criteria |
|---|---|---|
| M0 | `keys.py`, `specs.py`, `schema.py` | key/schema unit tests pass |
| M1 | `build.py` for presence features (condition/drug/procedure) | eras built, registry complete, idempotent |
| M2 | `read.py` windows + TARs + prevalence | one build, many TARs/cohorts |
| M3 | measurement value + value-as-concept + range group | continuous/categorical tests pass |
| M4 | `parity.py` + synthetic CDM + R harness | parity report for presence features |
| M5 | extend parity to value/observation/count features | full report with known divergences |
| M6 | batching/optimisation + docs | same rows, faster; `docs/design/era-cache.md` |

M1–M3 are the "initial implementation". M4–M5 are the parity programme. M6 can
follow.

## 10. Risks

| Risk | Mitigation |
|---|---|
| R/Java/Athena not available in CI | synthetic generator + optional parity workflow |
| FE template semantics differ subtly | known-divergence table + exact row-set sample check |
| Vocabulary bundle licensing/size | never commit; env var + manifest hash |
| Long builds failing mid-family | per-family staging + registry (PR 60 lesson) |
| Storage blow-up | selective caching; partition by feature_key/date |
| Scope creep into windows/aggregations in the key | key tests enforce D2 |
| DuckDB vs PostgreSQL numeric behaviour | parity runs on one fixed engine per report |

## 11. Open questions

1. Should measurement **value features** be separate `feature_key`s per unit, or
   one key with a unit filter at read time? (Recommended: one key, filter at read.)
2. Do we need an explicit `is_first` flag for `first=True` concepts, or store all
   eras and reduce at read? (Recommended: store all; reduce at read.)
3. Should the parity harness also cover `aggregated = FALSE` (row-level) exact
   comparison for a small sample, or prevalence only? (Recommended: both, with
   row-level limited to 20 features.)
4. Where does the cache schema live: results schema, a dedicated
   `feature_cache` schema, or both (configurable)? (Recommended: configurable,
   default dedicated schema.)
