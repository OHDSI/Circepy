from __future__ import annotations

import pytest

from circe.era_cache import ContinuousPredicate, EraFeatureSpec, era_feature_key


def test_key_is_content_addressed_and_ignores_display_fields():
    left = EraFeatureSpec(
        name="T2DM",
        source_table="condition_occurrence",
        concept_ids=(201826,),
        tags=("condition",),
    )
    right = EraFeatureSpec(
        name="Type 2 diabetes",
        source_table="condition_occurrence",
        concept_ids=(201826,),
    )
    assert era_feature_key(left) == era_feature_key(right)


def test_key_ignores_concept_order():
    left = EraFeatureSpec(name="x", source_table="condition_occurrence", concept_ids=(201826, 316139))
    right = EraFeatureSpec(name="x", source_table="condition_occurrence", concept_ids=(316139, 201826))
    assert era_feature_key(left) == era_feature_key(right)


def test_key_changes_with_selection():
    base = EraFeatureSpec(name="x", source_table="condition_occurrence", concept_ids=(201826,))
    other_concepts = EraFeatureSpec(name="x", source_table="condition_occurrence", concept_ids=(316139,))
    other_table = EraFeatureSpec(name="x", source_table="condition_era", concept_ids=(201826,))
    descendants = EraFeatureSpec(
        name="x",
        source_table="condition_occurrence",
        concept_ids=(201826,),
        include_descendants=True,
    )
    assert era_feature_key(base) != era_feature_key(other_concepts)
    assert era_feature_key(base) != era_feature_key(other_table)
    assert era_feature_key(base) != era_feature_key(descendants)


def test_key_does_not_include_windows_or_predicates():
    """The whole point of the cache: a window is not part of feature identity."""
    feature = EraFeatureSpec(
        name="hba1c",
        source_table="measurement",
        concept_ids=(3004410,),
        feature_class="continuous",
    )
    with_predicates = EraFeatureSpec(
        name="hba1c",
        source_table="measurement",
        concept_ids=(3004410,),
        feature_class="continuous",
        predicates=(ContinuousPredicate(op="gt", reference="range"),),
    )
    assert era_feature_key(feature) == era_feature_key(with_predicates)


def test_categorical_and_continuous_keys_differ():
    categorical = EraFeatureSpec(
        name="x",
        source_table="measurement",
        concept_ids=(3004410,),
        value_concept_ids=(4328749,),
        feature_class="categorical",
    )
    continuous = EraFeatureSpec(
        name="x", source_table="measurement", concept_ids=(3004410,), feature_class="continuous"
    )
    assert era_feature_key(categorical) != era_feature_key(continuous)


def test_spec_validation():
    with pytest.raises(ValueError):
        EraFeatureSpec(name="x", source_table="condition_occurrence")
    with pytest.raises(ValueError):
        EraFeatureSpec(
            name="x",
            source_table="condition_occurrence",
            concept_ids=(201826,),
            feature_class="continuous",
        )
    with pytest.raises(ValueError):
        EraFeatureSpec(
            name="x",
            source_table="measurement",
            concept_ids=(3004410,),
            feature_class="categorical",
        )
    with pytest.raises(ValueError):
        EraFeatureSpec(
            name="x",
            source_table="measurement",
            concept_ids=(3004410,),
            feature_class="continuous",
            value_concept_ids=(1,),
        )
    with pytest.raises(ValueError):
        EraFeatureSpec(
            name="x",
            source_table="condition_occurrence",
            concept_ids=(201826,),
            predicates=(ContinuousPredicate(op="gt", reference="range"),),
        )


def test_continuous_predicate_validation():
    with pytest.raises(ValueError):
        ContinuousPredicate(op="gt")
    with pytest.raises(ValueError):
        ContinuousPredicate(op="between", threshold=1.0)
    with pytest.raises(ValueError):
        ContinuousPredicate(op="between", reference="range", threshold=1.0)
    predicate = ContinuousPredicate(op="between", threshold=1.0, upper=5.0)
    assert predicate.describe() == "value:1.0..5.0"
