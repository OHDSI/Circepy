"""Value features: continuous values and observed categorical value concepts.

These run on DuckDB only.  The local Spark CDM has no populated measurement
values, so this is the coverage that exercises value reads end to end.
"""

from __future__ import annotations

import pandas as pd

from circe.era_cache import (
    CohortEraSpec,
    EraFeatureSpec,
    build_era_cache,
    era_feature_key,
    feature_membership,
    feature_values,
    load_cohort,
)

HBA1C = 3004410
GLUCOSE = 3004411
HIGH = 4328749
NORMAL = 4069590


def _specs():
    return {
        "hba1c_value": EraFeatureSpec(
            name="hba1c_value",
            source_table="measurement",
            concept_ids=(HBA1C,),
            feature_class="continuous",
        ),
        "hba1c_high_concept": EraFeatureSpec(
            name="hba1c_high_concept",
            source_table="measurement",
            concept_ids=(HBA1C,),
            feature_class="categorical",
            value_concept_ids=(HIGH,),
        ),
        "glucose_high_concept": EraFeatureSpec(
            name="glucose_high_concept",
            source_table="measurement",
            concept_ids=(GLUCOSE,),
            feature_class="categorical",
            value_concept_ids=(HIGH,),
        ),
        "glucose_units": EraFeatureSpec(
            name="glucose_units",
            source_table="measurement",
            concept_ids=(GLUCOSE,),
            feature_class="continuous",
            unit_concept_ids=(8753,),
        ),
    }


def _built(backend):
    specs = _specs()
    build_era_cache(
        list(specs.values()),
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        force=True,
    )
    return specs, {era_feature_key(spec): name for name, spec in specs.items()}


def _values(backend, key, window=None):
    window = window or CohortEraSpec(-3650, 0)
    return feature_values(
        load_cohort(backend.table("cohort"), cohort_id=1),
        window=window,
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
    ).execute()[lambda frame: frame["feature_key"] == key]


def test_categorical_value_concept_is_an_observed_concept(backend):
    specs, _ = _built(backend)
    rows = backend.table("era_feature_categorical", database="feature_cache").execute()
    high = rows[rows["feature_key"] == era_feature_key(specs["hba1c_high_concept"])]
    # Only person 1 has an HbA1c flagged High; person 2's High row is glucose.
    assert len(high) == 1
    assert set(high["value_concept_id"]) == {HIGH}


def test_categorical_prevalence_uses_the_value_concept(backend):
    specs, key_to_name = _built(backend)
    membership = feature_membership(
        load_cohort(backend.table("cohort"), cohort_id=1),
        windows=[CohortEraSpec(-3650, 0)],
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
    ).execute()
    found = set(membership["feature_key"])
    assert era_feature_key(specs["hba1c_high_concept"]) in found
    assert era_feature_key(specs["glucose_high_concept"]) in found
    assert key_to_name[era_feature_key(specs["hba1c_high_concept"])] == "hba1c_high_concept"


def test_value_concept_missing_means_no_categorical_rows(backend):
    """A value concept that never occurs must not fabricate rows."""
    spec = EraFeatureSpec(
        name="never",
        source_table="measurement",
        concept_ids=(HBA1C,),
        feature_class="categorical",
        value_concept_ids=(999999,),
    )
    outcome = build_era_cache(
        [spec], backend=backend, cache_schema="feature_cache", cdm_schema="main", force=True
    )
    assert outcome.failed
    assert outcome.failed[0]["error"] == "feature produced no rows"


def test_continuous_values_are_stored_with_ranges(backend):
    specs, _ = _built(backend)
    key = era_feature_key(specs["hba1c_value"])
    rows = backend.table("era_feature_continuous", database="feature_cache").execute()
    hba1c = rows[rows["feature_key"] == key]
    assert len(hba1c) == 3
    assert hba1c["value_num"].notnull().all()
    assert set(hba1c["range_high"]) == {6.0}


def test_last_value_is_latest_not_maximum(backend):
    specs, _ = _built(backend)
    key = era_feature_key(specs["hba1c_value"])
    rows = _values(backend, key)
    person_one = rows[rows["row_id"] == 1].iloc[0]
    # 9.2 (2019-07-01) then 7.1 (2020-07-20): the last value is 7.1.
    assert person_one["num_events"] == 2
    assert person_one["max_value"] == 9.2
    assert person_one["last_value"] == 7.1


def test_above_normal_uses_reference_range(backend):
    specs, _ = _built(backend)
    key = era_feature_key(specs["hba1c_value"])
    above = feature_values(
        load_cohort(backend.table("cohort"), cohort_id=1),
        window=CohortEraSpec(-3650, 0),
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
        predicate="above_normal",
    ).execute()
    above = above[above["feature_key"] == key]
    person_one = above[above["row_id"] == 1].iloc[0]
    assert person_one["num_events"] == 2
    assert person_one["min_value"] == 7.1
    assert person_one["max_value"] == 9.2


def test_within_normal_and_below_normal(backend):
    specs, _ = _built(backend)
    key = era_feature_key(specs["hba1c_value"])
    cohort = load_cohort(backend.table("cohort"), cohort_id=1)
    window = CohortEraSpec(-3650, 0)
    for predicate in ("within_normal", "below_normal"):
        rows = feature_values(
            cohort,
            window=window,
            backend=backend,
            cache_schema="feature_cache",
            observation_period=backend.table("observation_period"),
            predicate=predicate,
        ).execute()
        rows = rows[rows["feature_key"] == key]
        # Person 4 has HbA1c 6.0 with range 4-6: within normal, never below.
        if predicate == "within_normal":
            assert 4 in set(rows["row_id"])
        else:
            assert 4 not in set(rows["row_id"])


def test_null_value_never_matches_a_numeric_predicate(backend):
    specs, _ = _built(backend)
    key = era_feature_key(specs["glucose_units"])
    rows = backend.table("era_feature_continuous", database="feature_cache").execute()
    glucose = rows[rows["feature_key"] == key]
    # Person 3's glucose has no value; it is stored but has no number.
    assert glucose["value_num"].isnull().any()

    above = feature_values(
        load_cohort(backend.table("cohort"), cohort_id=1),
        window=CohortEraSpec(-3650, 0),
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
        predicate="above_normal",
    ).execute()
    above = above[above["feature_key"] == key]
    assert 3 not in set(above["row_id"])


def test_unit_filter_restricts_rows(backend):
    specs, _ = _built(backend)
    key = era_feature_key(specs["glucose_units"])
    rows = backend.table("era_feature_continuous", database="feature_cache").execute()
    glucose = rows[rows["feature_key"] == key]
    assert set(glucose["unit_concept_id"]) == {8753}


def test_value_rows_are_deduplicated(backend):
    """Duplicate CDM rows collapse to one era."""
    backend.insert(
        "measurement",
        pd.DataFrame(
            {
                "measurement_id": [999],
                "person_id": [1],
                "measurement_concept_id": [HBA1C],
                "measurement_date": pd.Series(pd.to_datetime(["2020-07-20"]).date),
                "value_as_number": [7.1],
                "value_as_concept_id": [NORMAL],
                "unit_concept_id": [8840],
                "range_low": [4.0],
                "range_high": [6.0],
                "operator_concept_id": [0],
            }
        ),
    )
    specs, _ = _built(backend)
    key = era_feature_key(specs["hba1c_value"])
    rows = _values(backend, key)
    person_one = rows[rows["row_id"] == 1].iloc[0]
    assert person_one["num_events"] == 2
