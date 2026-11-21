# Cohort-first feature extraction (`circe.cohort_features`)

This package implements the basic feature-extraction layer on top of the
decomposable cohort templates branch. It lives in its own folder so it does not
collide with the richer `circe.features` work.

The design principle is a duality:

- **Any cohort can be a feature.** A cohort definition is executed and its
  membership becomes a covariate for a target population.
- **Any feature can be a cohort.** A feature is a cohort expression plus a
  window and an aggregation; `to_cohort()` returns a normal CIRCE definition
  that can be generated, exported, or reused in another cohort.

## Public API

```python
from circe.cohort_features import (
    CohortFeature,
    CriteriaFeature,
    FeatureSet,
    FeatureWindow,
    cohort_to_feature,
    feature_to_cohort,
    feature_to_criteria_group,
    CohortTemplate,
    FeatureTemplate,
    extract_feature_matrix,
)
```

### Any cohort as a feature

```python
from circe.cohort_definition_set import load_cohort_definition_set

cohorts = load_cohort_definition_set("path/to/cohorts")
features = FeatureSet.from_cohort_definition_set(
    cohorts,
    window=FeatureWindow(start_days=-365, end_days=0),
)
```

### Feature as a cohort

```python
feature = cohort_to_feature(cohort_expression, feature_id=10, name="T2DM")
cohort_expression_again = feature_to_cohort(feature)
assert cohort_expression_again.checksum() == cohort_expression.checksum()
```

A feature that is a pure primary-criteria selection can also be projected back
to a `CriteriaGroup` for reuse inside another cohort definition:

```python
group = feature_to_criteria_group(feature)
```

Cohorts with additional criteria or inclusion rules raise
`NotExpressibleAsCriteriaError`; convert those with `to_cohort()` instead.

### Criteria-first features

```python
from circe.cohortdefinition import ConditionOccurrence
from circe.cohort_features import criteria_feature

feature = criteria_feature(
    ConditionOccurrence(codeset_id=1),
    feature_id=1,
    concept_sets=[concept_set],
    window=FeatureWindow(start_days=-365, end_days=0),
)
cohort = feature.to_cohort()
```

### Decomposable templates

`CohortTemplate` pairs a base cohort with refinements from
`circe.decomposition.operators`:

```python
from circe.decomposition.operators import RequireAtEntry

template = CohortTemplate(name="T2DM", base=t2dm_cohort).variant(
    "T2DM + metformin", RequireAtEntry(drug_group)
)
feature = template.to_feature(feature_id=4, name="T2DM + metformin")
```

`flatten()` applies refinements to a copy of the base; the base is never
mutated. `decompose()` returns the base and refinements. `expand_templates()`
turns a list of templates into a `FeatureSet`.

`FeatureTemplate` does the same for an existing `CohortFeature`.

## Extraction

`extract_feature_matrix()`:

1. converts the feature set to a `CohortDefinitionSet`;
2. generates the feature cohorts with `generate_cohort_set(..., shared=True)`;
3. joins the target population to each feature cohort on `subject_id`;
4. applies the feature window relative to the target index date;
5. aggregates with `exists` or `count`;
6. optionally fills zeros for every target/feature pair.

```python
matrix = extract_feature_matrix(
    features,
    backend=conn,
    cdm_schema="cdm",
    target_cohort_table="cohort",
    target_cohort_id=1,
    feature_cohort_table="feature_cohort",
    results_schema="results",
    shared=True,
    include_zeros=True,
)
matrix.values  # lazy (row_id, feature_id, value)
matrix.feature_ref  # feature metadata
matrix.write(conn, schema="results")
```

### Output contract

- `feature_matrix`: `row_id` (int64), `feature_id` (int64), `value` (float64).
- `feature_ref`: `feature_id`, `name`, `aggregation`, window fields, tags.

`row_id` defaults to the target table's `subject_id`. If the target cohort can
contain multiple entries per subject, pass `row_id_column` to select a unique
row identifier, or deduplicate the target cohort.

## What is supported

- Cohort expressions with concept sets, primary criteria, additional criteria,
  inclusion rules, end strategies and censoring (executed by the existing
  engine).
- `exists` and `count` aggregations.
- Relative windows (`start_days`, `end_days`, start/end basis, interval overlap).
  Pass `window=None` for "ever before/after" without a time filter.
- Dense (zeros included) or sparse output.
- Shared vs serial cohort generation; both produce the same matrix.
- Feature metadata and materialisation to database tables.

## What is intentionally not here

- Value features (lab values, units), temporal grids and sequence tokens —
  those belong in `circe.features` / a future sequence layer.
- Model training, embeddings and causal estimators.
- Automatic row-identity derivation for multi-entry target cohorts.
- Observation-period truncation beyond what the cohort engine already applies.

## Tests

`tests/cohort_features/` covers:

- cohort → feature → cohort round trips;
- feature → criteria group projection and the expected failure for refined
  cohorts;
- template flattening, decomposition and variants;
- basic matrix extraction, sparse/dense output, shared vs serial generation and
  materialisation.

Run with:

```bash
pytest tests/cohort_features
```
