from __future__ import annotations

from circe.cohort_features import (
    CohortFeature,
    CohortTemplate,
    FeatureSet,
    cohort_to_feature,
    extract_feature_matrix,
)
from circe.decomposition.operators import RequireAtEntry

from .helpers import concept_set, condition_cohort, drug_cohort, drug_criteria_group


def _features():
    t2dm = cohort_to_feature(condition_cohort(201826, "T2DM"), feature_id=1, name="T2DM")
    chf = cohort_to_feature(condition_cohort(316139, "CHF"), feature_id=2, name="CHF")
    metformin = cohort_to_feature(drug_cohort(1503297, "Metformin"), feature_id=3, name="Metformin")

    base = condition_cohort(201826, "T2DM")
    base.concept_sets = [*base.concept_sets, concept_set(1503297, 2)]
    combined = CohortTemplate(
        name="T2DM plus metformin",
        base=base,
        refinements=(RequireAtEntry(drug_criteria_group(codeset_id=2)),),
    ).to_feature(feature_id=4, name="T2DM plus metformin")

    count = CohortFeature(
        feature_id=5,
        name="T2DM count",
        cohort=condition_cohort(201826, "T2DM"),
        aggregation="count",
    )
    return FeatureSet(features=[t2dm, chf, metformin, combined, count])


def _as_dict(matrix):
    frame = matrix.values.execute()
    return {(int(row.row_id), int(row.feature_id)): float(row.value) for row in frame.itertuples(index=False)}


def test_basic_feature_matrix(backend):
    matrix = extract_feature_matrix(
        _features(),
        backend=backend,
        cdm_schema="main",
        target_cohort_table="cohort",
        target_cohort_id=1,
        feature_cohort_table="feature_cohort",
        include_zeros=True,
    )
    values = _as_dict(matrix)
    assert len(values) == 15  # 3 target rows x 5 features

    assert values[(1, 1)] == 1.0
    assert values[(1, 2)] == 1.0
    assert values[(1, 3)] == 1.0
    assert values[(1, 4)] == 1.0
    assert values[(1, 5)] == 2.0

    assert values[(2, 1)] == 0.0
    assert values[(2, 2)] == 1.0
    assert values[(2, 3)] == 1.0
    assert values[(2, 4)] == 0.0
    assert values[(2, 5)] == 0.0

    assert values[(3, 1)] == 1.0
    assert values[(3, 2)] == 0.0
    assert values[(3, 3)] == 0.0
    assert values[(3, 4)] == 0.0
    assert values[(3, 5)] == 1.0

    ref = matrix.feature_ref.execute()
    assert list(ref["feature_id"]) == [1, 2, 3, 4, 5]
    assert list(ref["name"]) == ["T2DM", "CHF", "Metformin", "T2DM plus metformin", "T2DM count"]


def test_sparse_output_omits_zero_rows(backend):
    matrix = extract_feature_matrix(
        _features(),
        backend=backend,
        cdm_schema="main",
        target_cohort_table="cohort",
        target_cohort_id=1,
        feature_cohort_table="feature_cohort_sparse",
        include_zeros=False,
    )
    values = _as_dict(matrix)
    assert len(values) == 9
    assert (2, 1) not in values
    assert values[(2, 2)] == 1.0


def test_shared_and_serial_generation_produce_the_same_matrix(backend):
    shared = extract_feature_matrix(
        _features(),
        backend=backend,
        cdm_schema="main",
        target_cohort_table="cohort",
        target_cohort_id=1,
        feature_cohort_table="feature_cohort_shared",
        shared=True,
    )
    serial = extract_feature_matrix(
        _features(),
        backend=backend,
        cdm_schema="main",
        target_cohort_table="cohort",
        target_cohort_id=1,
        feature_cohort_table="feature_cohort_serial",
        shared=False,
    )
    assert _as_dict(shared) == _as_dict(serial)


def test_feature_matrix_can_be_written(backend):
    matrix = extract_feature_matrix(
        _features(),
        backend=backend,
        cdm_schema="main",
        target_cohort_table="cohort",
        target_cohort_id=1,
        feature_cohort_table="feature_cohort_write",
    )
    names = matrix.write(backend, schema=None)
    assert names == {"values": "feature_matrix", "feature_ref": "feature_ref"}
    assert int(backend.table("feature_matrix").count().execute()) == 15
    assert int(backend.table("feature_ref").count().execute()) == 5


def test_window_none_uses_full_history(backend):
    import pandas as pd

    backend.insert(
        "condition_occurrence",
        pd.DataFrame(
            {
                "condition_occurrence_id": [900],
                "person_id": [2],
                "condition_concept_id": [201826],
                "condition_start_date": pd.Series(pd.to_datetime(["2019-06-01"]).date),
                "condition_end_date": pd.Series(pd.to_datetime(["2019-06-05"]).date),
            }
        ),
    )
    feature = cohort_to_feature(
        condition_cohort(201826, "T2DM ever"),
        feature_id=1,
        name="T2DM ever",
        window=None,
    )
    matrix = extract_feature_matrix(
        FeatureSet(features=[feature]),
        backend=backend,
        cdm_schema="main",
        target_cohort_table="cohort",
        target_cohort_id=1,
        feature_cohort_table="feature_cohort_any_time",
        include_zeros=True,
    )
    values = _as_dict(matrix)
    assert values[(2, 1)] == 1.0
