from __future__ import annotations

import pytest

from circe.cohort_features import (
    CohortFeature,
    FeatureSet,
    FeatureWindow,
    NotExpressibleAsCriteriaError,
    cohort_to_feature,
    criteria_feature,
    feature_to_cohort,
    feature_to_criteria_group,
    features_from_cohort_set,
)
from circe.cohortdefinition import ConditionOccurrence, ObservationFilter
from circe.vocabulary import ConceptSet

from .helpers import concept_set, condition_cohort, drug_cohort, drug_criteria_group


def test_any_cohort_can_be_a_feature_and_back_unchanged():
    expression = condition_cohort(201826, "T2DM")
    feature = cohort_to_feature(expression, feature_id=7, name="T2DM")
    assert feature.feature_id == 7
    assert feature_to_cohort(feature).checksum() == expression.checksum()


def test_criteria_feature_turns_into_a_cohort_and_back():
    concept_sets = (concept_set(201826, 1),)
    feature = criteria_feature(
        ConditionOccurrence(codeset_id=1),
        feature_id=3,
        name="T2DM",
        concept_sets=concept_sets,
        observation_window=ObservationFilter(prior_days=0, post_days=0),
    )
    expression = feature.to_cohort()
    assert expression.primary_criteria is not None
    assert expression.primary_criteria.criteria_list
    assert expression.concept_sets[0].id == 1

    wrapped = CohortFeature(
        feature_id=feature.feature_id,
        name=feature.name,
        cohort=expression,
    )
    assert wrapped.checksum() == feature.checksum()


def test_pure_cohort_projects_to_criteria_group():
    feature = cohort_to_feature(condition_cohort(201826, "T2DM"), feature_id=1)
    group = feature_to_criteria_group(feature)
    assert group.criteria_list
    assert group.type == "ALL"


def test_cohort_with_additional_criteria_cannot_project_to_one_group():
    base = condition_cohort(201826, "T2DM")
    base.concept_sets = [*base.concept_sets, concept_set(1503297, 2)]
    base.additional_criteria = drug_criteria_group(codeset_id=2)
    feature = cohort_to_feature(base, feature_id=1)
    with pytest.raises(NotExpressibleAsCriteriaError):
        feature_to_criteria_group(feature)


def test_feature_set_round_trips_through_cohort_definition_set():
    features = FeatureSet(
        features=[
            cohort_to_feature(condition_cohort(201826, "T2DM"), feature_id=10, name="T2DM"),
            cohort_to_feature(drug_cohort(1503297, "Metformin"), feature_id=11, name="Metformin"),
        ]
    )
    cohort_set = features.to_cohort_definition_set()
    assert [definition.cohort_id for definition in cohort_set] == [10, 11]
    assert [definition.cohort_name for definition in cohort_set] == ["T2DM", "Metformin"]

    restored = features_from_cohort_set(cohort_set)
    assert [feature.feature_id for feature in restored] == [10, 11]
    assert [feature.checksum() for feature in restored] == [feature.checksum() for feature in features]


def test_feature_window_validation():
    with pytest.raises(ValueError):
        FeatureWindow(start_days=10, end_days=0)
    window = FeatureWindow(start_days=None, end_days=0)
    assert window.start_days is None


def test_feature_set_rejects_duplicate_ids():
    first = cohort_to_feature(condition_cohort(201826, "T2DM"), feature_id=1)
    second = cohort_to_feature(drug_cohort(1503297, "Metformin"), feature_id=1)
    with pytest.raises(ValueError):
        FeatureSet(features=[first, second])


def test_criteria_feature_accepts_plain_concept_sets():
    concept_sets = (ConceptSet(id=1, expression=None),)
    feature = criteria_feature(
        ConditionOccurrence(codeset_id=1),
        feature_id=1,
        concept_sets=concept_sets,
    )
    assert len(feature.to_cohort().concept_sets) == 1
