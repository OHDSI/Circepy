from __future__ import annotations

import pandas as pd

from circe.era_cache import (
    CohortEraSpec,
    EraFeatureSpec,
    build_cohort_eras,
    build_era_cache,
    era_feature_key,
    feature_membership,
    feature_values,
    load_cohort,
    prevalence,
)
from circe.era_cache.scope import cohort_scope


def _specs():
    return {
        "t2dm": EraFeatureSpec(name="t2dm", source_table="condition_occurrence", concept_ids=(201826,)),
        "chf": EraFeatureSpec(name="chf", source_table="condition_occurrence", concept_ids=(316139,)),
        "hba1c": EraFeatureSpec(
            name="hba1c",
            source_table="measurement",
            concept_ids=(3004410,),
            feature_class="continuous",
        ),
        "hba1c_high": EraFeatureSpec(
            name="hba1c_high",
            source_table="measurement",
            concept_ids=(3004410,),
            feature_class="categorical",
            value_concept_ids=(4328749,),
        ),
    }


def _built(backend, specs):
    build_era_cache(
        list(specs.values()),
        backend=backend,
        cache_schema="feature_cache",
        cdm_schema="main",
        force=True,
        scope=cohort_scope(1, cohort_table="cohort"),
    )
    return {era_feature_key(spec): name for name, spec in specs.items()}


def _cohort(backend, cohort_id=1):
    return load_cohort(backend.table("cohort"), cohort_id=cohort_id)


def _prevalence(backend, windows):
    specs = _specs()
    key_to_name = _built(backend, specs)
    result = prevalence(
        _cohort(backend),
        windows=windows,
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
    ).execute()
    result["name"] = result["feature_key"].map(key_to_name)
    return result.set_index(["name", "window_index"])["prevalence"].to_dict()


def test_window_changes_prevalence_without_rebuilding(backend):
    values = _prevalence(
        backend,
        [CohortEraSpec(-365, 0), CohortEraSpec(-365, 365), CohortEraSpec(-30, 30)],
    )
    # T2DM: person 1 in 2017 (outside a year, outside the observation period),
    # person 3 in 2020-11-01 (only the symmetric window reaches it).
    assert values[("t2dm", 0)] == 0.0
    assert values[("t2dm", 1)] == 0.25
    # CHF: person 1 in 2020-07-15 and person 2 in 2020-03-01 (inside a year),
    # only person 1 inside +/-30 days.
    assert values[("chf", 0)] == 0.5
    assert values[("chf", 1)] == 0.5
    assert values[("chf", 2)] == 0.25


def test_membership_reports_window_index(backend):
    specs = _specs()
    _built(backend, specs)
    membership = feature_membership(
        _cohort(backend),
        windows=[CohortEraSpec(-30, 30)],
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
    ).execute()
    assert set(membership["window_index"]) == {0}
    assert set(membership["row_id"]) == {1}


def test_cohort_eras_clamp_to_observation_period(backend):
    cohort = _cohort(backend)
    eras = build_cohort_eras(
        cohort,
        eras=[CohortEraSpec(-10000, 0)],
        observation_period=backend.table("observation_period"),
    ).execute()
    assert (pd.to_datetime(eras["start_day"]) >= pd.Timestamp("2018-01-01")).all()


def test_cohort_eras_drop_inverted_windows(backend):
    cohort = _cohort(backend)
    eras = build_cohort_eras(
        cohort,
        eras=[CohortEraSpec(900, 1000)],
        observation_period=backend.table("observation_period"),
    ).execute()
    # The window starts after the observation period ends, so it is dropped.
    assert len(eras) == 0


def test_feature_values_last_is_latest_event(backend):
    specs = _specs()
    _built(backend, specs)
    values = feature_values(
        _cohort(backend),
        window=CohortEraSpec(-365, 0),
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
    ).execute()
    hba1c = values[values["feature_key"] == era_feature_key(specs["hba1c"])]
    person_one = hba1c[hba1c["row_id"] == 1].iloc[0]
    # Person 1 has HbA1c 9.2 in 2019 and 7.1 in 2020-07-20; last is 7.1.
    assert person_one["last_value"] == 7.1
    assert person_one["max_value"] == 7.1
    assert person_one["num_events"] == 1


def test_above_normal_predicate_filters_values(backend):
    specs = _specs()
    _built(backend, specs)
    window = CohortEraSpec(-3650, 0)
    below = feature_values(
        _cohort(backend),
        window=window,
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
    ).execute()
    above = feature_values(
        _cohort(backend),
        window=window,
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
        predicate="above_normal",
    ).execute()
    hba1c_key = era_feature_key(specs["hba1c"])
    person_one_all = below[(below["row_id"] == 1) & (below["feature_key"] == hba1c_key)]
    person_one_high = above[(above["row_id"] == 1) & (above["feature_key"] == hba1c_key)]
    # Person 1 has two HbA1c results inside a ten-year window: 9.2 (2019-07-01)
    # and 7.1 (2020-07-20). Both exceed range_high 6.0, so both are above normal.
    assert person_one_all["num_events"].iloc[0] == 2
    assert person_one_high["num_events"].iloc[0] == 2
    assert person_one_high["min_value"].iloc[0] == 7.1
    assert person_one_high["max_value"].iloc[0] == 9.2


def test_one_build_serves_two_cohorts(backend):
    specs = _specs()
    key_to_name = _built(backend, specs)
    # Add a second cohort with a different index date.
    backend.insert(
        "cohort",
        pd.DataFrame(
            {
                "cohort_definition_id": [2, 2, 2, 2],
                "subject_id": [1, 2, 3, 4],
                "cohort_start_date": pd.Series(pd.to_datetime(["2021-01-01"] * 4).date),
                "cohort_end_date": pd.Series(pd.to_datetime(["2021-12-31"] * 4).date),
            }
        ),
    )
    windows = [CohortEraSpec(-365, 0)]
    results = {}
    for cohort_id in (1, 2):
        frame = prevalence(
            load_cohort(backend.table("cohort"), cohort_id=cohort_id),
            windows=windows,
            backend=backend,
            cache_schema="feature_cache",
            observation_period=backend.table("observation_period"),
        ).execute()
        frame["name"] = frame["feature_key"].map(key_to_name)
        results[cohort_id] = frame.set_index("name")["prevalence"].to_dict()

    # Both cohorts see person 1 (2020-07-15) and person 2 (2020-03-01) inside a
    # one-year window of their own index dates; the cache is built only once.
    assert results[1]["chf"] == 0.5
    assert results[2]["chf"] == 0.5
    # Both reads came from the same cache rows.
    assert int(backend.table("era_feature_presence", database="feature_cache").count().execute()) > 0


def test_missing_cache_tables_raise_a_clear_error(backend):
    import pytest

    # DuckDB raises a catalog/missing-table error for an unknown schema.
    with pytest.raises(Exception):  # noqa: B017 - backend error type varies
        prevalence(
            _cohort(backend),
            windows=[CohortEraSpec(-365, 0)],
            backend=backend,
            cache_schema="no_such_schema",
        )


def test_selective_feature_read(backend):
    specs = _specs()
    _built(backend, specs)
    membership = feature_membership(
        _cohort(backend),
        windows=[CohortEraSpec(-365, 0)],
        backend=backend,
        cache_schema="feature_cache",
        observation_period=backend.table("observation_period"),
        feature_keys=[era_feature_key(specs["chf"])],
    ).execute()
    assert set(membership["feature_key"]) == {era_feature_key(specs["chf"])}
