"""Tests for cohort-as-feature overlap matrices."""

from __future__ import annotations

import pytest

from circe.cohort_definition_set._core import CohortDefinitionSet
from circe.cohort_features import (
    FeatureWindow,
    cohort_overlap_features,
    cohort_overlap_from_set,
    cohort_overlap_pairs,
    pairs_by_target,
)
from circe.cohort_features.cohort_as_feature import feature_id_for_pair

from .helpers import condition_cohort


def _cohort_set(*concept_ids: int) -> CohortDefinitionSet:
    definitions = CohortDefinitionSet()
    for index, concept_id in enumerate(concept_ids, start=1):
        definitions.add(
            cohort_id=index,
            cohort_name=f"cohort_{concept_id}",
            expression=condition_cohort(concept_id, f"cohort_{concept_id}"),
        )
    return definitions


def test_pairs_exclude_self_by_default():
    pairs = list(cohort_overlap_pairs(_cohort_set(1, 2, 3)))

    assert len(pairs) == 6  # 3 targets x 2 features
    assert all(pair.target_cohort_id != pair.feature_cohort_id for pair in pairs)


def test_pairs_include_self_when_asked():
    pairs = list(cohort_overlap_pairs(_cohort_set(1, 2), include_self=True))

    assert len(pairs) == 4
    assert any(pair.target_cohort_id == pair.feature_cohort_id for pair in pairs)


def test_feature_ids_are_unique_and_dense():
    pairs = list(cohort_overlap_pairs(_cohort_set(1, 2, 3)))
    ids = [pair.feature_id for pair in pairs]

    assert ids == list(range(1, len(pairs) + 1))


def test_pair_ordering_is_target_major():
    pairs = list(cohort_overlap_pairs(_cohort_set(10, 20, 30)))

    assert [pair.target_cohort_id for pair in pairs] == [1, 1, 2, 2, 3, 3]
    assert [pair.feature_cohort_id for pair in pairs] == [2, 3, 1, 3, 1, 2]


def test_max_features_per_target_caps_each_target():
    pairs = list(cohort_overlap_pairs(_cohort_set(1, 2, 3, 4), max_features_per_target=2))

    grouped = pairs_by_target(pairs)
    assert set(grouped) == {1, 2, 3, 4}
    assert all(len(group) == 2 for group in grouped.values())


def test_max_features_per_target_rejects_non_positive():
    with pytest.raises(ValueError, match="must be >= 1"):
        list(cohort_overlap_pairs(_cohort_set(1, 2), max_features_per_target=0))


def test_single_cohort_has_no_pairs():
    assert list(cohort_overlap_pairs(_cohort_set(1))) == []


def test_single_cohort_overlap_only_with_self():
    pairs = list(cohort_overlap_pairs(_cohort_set(1), include_self=True))

    assert len(pairs) == 1
    assert pairs[0].target_cohort_id == 1
    assert pairs[0].feature_cohort_id == 1


def test_overlap_features_carry_the_window_and_tag():
    feature_set = cohort_overlap_features(
        _cohort_set(1, 2),
        window=FeatureWindow(start_days=-30, end_days=0, overlap=True),
    )

    assert len(feature_set) == 2
    for feature in feature_set.features:
        assert feature.window.start_days == -30
        assert feature.window.overlap is True
        assert "cohort_overlap" in feature.tags


def test_overlap_features_use_the_feature_cohort_expression():
    cohort_set = _cohort_set(1, 2)
    feature_set = cohort_overlap_features(cohort_set)

    feature_concept_ids = {feature.source_cohort_id for feature in feature_set.features}
    assert feature_concept_ids == {1, 2}
    assert all(feature.aggregation == "exists" for feature in feature_set.features)


def test_overlap_from_set_keeps_pairs_aligned_with_features():
    cohort_set = _cohort_set(1, 2, 3)
    feature_set, pairs = cohort_overlap_from_set(cohort_set)

    assert len(feature_set.features) == len(pairs)
    for pair, feature in zip(pairs, feature_set.features, strict=True):
        assert pair.feature_id == feature.feature_id
        assert pair.feature_cohort_id == feature.source_cohort_id


def test_overlap_from_set_rejects_a_single_cohort():
    with pytest.raises(ValueError, match="no overlap pairs"):
        cohort_overlap_from_set(_cohort_set(1))


def test_pair_names_reference_the_feature_cohort():
    pairs = list(cohort_overlap_pairs(_cohort_set(1, 2)))

    assert pairs[0].feature_cohort_name == "cohort_2"
    assert pairs[1].feature_cohort_name == "cohort_1"


def test_pairs_by_target_groups_in_order():
    pairs = list(cohort_overlap_pairs(_cohort_set(1, 2, 3)))
    grouped = pairs_by_target(pairs)

    assert list(grouped) == [1, 2, 3]
    assert [pair.feature_cohort_id for pair in grouped[1]] == [2, 3]


def test_feature_id_for_pair_is_stable_and_distinct():
    first = feature_id_for_pair(1, 2)
    second = feature_id_for_pair(1, 3)

    assert first == feature_id_for_pair(1, 2)
    assert first != second


def test_feature_id_for_pair_validates_base():
    with pytest.raises(ValueError, match="base must be >= 1"):
        feature_id_for_pair(1, 2, base=0)


def test_overlap_features_are_reusable_as_a_feature_set():
    """The overlap set is a normal FeatureSet, so it converts to cohorts."""
    cohort_set = _cohort_set(1, 2)
    feature_set = cohort_overlap_features(cohort_set)

    definition_set = feature_set.to_cohort_definition_set()
    assert len(list(definition_set)) == len(feature_set)


def test_overlap_window_matches_featureextraction_semantics():
    """Mirror CohortBasedBinaryCovariates.sql.

    R tests ``cohort_start <= index + end_day`` AND
    ``coalesce(cohort_end, cohort_start) >= index + start_day``; the interval
    intersects rather than the start date falling inside the window.
    """
    window = FeatureWindow(start_days=-365, end_days=0, overlap=True)
    feature_set = cohort_overlap_features(_cohort_set(1, 2), window=window)

    for feature in feature_set.features:
        assert feature.window.overlap is True
        assert feature.window.end_days == 0
        assert feature.window.start_days == -365


def test_default_window_is_one_year_prior():
    feature_set = cohort_overlap_features(_cohort_set(1, 2))
    window = feature_set.features[0].window

    assert window.start_days == -365
    assert window.end_days == 0


def test_overlap_features_are_binary_exists_aggregation():
    """R emits is_binary='Y', one row per (entry, cohort) pair."""
    feature_set = cohort_overlap_features(_cohort_set(1, 2))

    assert all(feature.aggregation == "exists" for feature in feature_set.features)
    assert all(feature.source_cohort_id is not None for feature in feature_set.features)
