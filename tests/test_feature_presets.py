"""
Tests for pre-built covariate presets (default, large-scale, Charlson).
"""

from __future__ import annotations

import pytest


class TestDefaultCovariates:
    def test_returns_feature_set(self):
        from circe.features.presets import default_covariates
        from circe.features.models import FeatureSet

        fs = default_covariates()
        assert isinstance(fs, FeatureSet)
        assert fs.name == "Default Covariates"

    def test_default_includes_demographics_and_domains(self):
        from circe.features.presets import default_covariates
        from circe.features.models import (
            BulkDomainFeature, DemographicsFeature, VisitCountFeature,
        )

        fs = default_covariates()
        types = [type(f) for f in fs]
        assert DemographicsFeature in types
        assert BulkDomainFeature in types
        assert VisitCountFeature in types

    def test_default_has_expected_count(self):
        from circe.features.presets import default_covariates

        fs = default_covariates()
        # 1 demographics + 3 bulk domains + 1 visit count = 5
        assert len(fs) == 5

    def test_disable_demographics(self):
        from circe.features.presets import default_covariates
        from circe.features.models import DemographicsFeature

        fs = default_covariates(include_demographics=False)
        types = [type(f) for f in fs]
        assert DemographicsFeature not in types
        assert len(fs) == 4  # 3 bulk + 1 visit


class TestLargeScaleCovariates:
    def test_returns_feature_set(self):
        from circe.features.presets import large_scale_covariates
        from circe.features.models import FeatureSet

        fs = large_scale_covariates()
        assert isinstance(fs, FeatureSet)

    def test_default_structure(self):
        from circe.features.presets import large_scale_covariates

        fs = large_scale_covariates()
        # 1 demographics + (8 domains + 1 visit) × 3 windows = 1 + 27 = 28
        assert len(fs) == 28

    def test_custom_domains_and_windows(self):
        from circe.features.presets import large_scale_covariates

        fs = large_scale_covariates(
            domains=["ConditionOccurrence", "DrugExposure"],
            windows=[(-30, 0), (-365, 0)],
            include_demographics=False,
            include_visits=False,
        )
        # 2 domains × 2 windows = 4
        assert len(fs) == 4


class TestCharlsonIndex:
    def test_returns_composite_feature(self):
        from circe.features.presets import charlson_index
        from circe.features.models import CompositeFeature

        feature = charlson_index()
        assert isinstance(feature, CompositeFeature)
        assert feature.name == "Charlson Comorbidity Index"

    def test_has_17_components(self):
        from circe.features.presets import charlson_index

        feature = charlson_index()
        assert len(feature.components) == 17

    def test_weights_match_r_implementation(self):
        from circe.features.presets import charlson_index, CHARLSON_COMPONENTS

        feature = charlson_index()

        for (expected_name, expected_weight, _), (actual_feature, actual_weight) in zip(
            CHARLSON_COMPONENTS, feature.components
        ):
            assert actual_feature.name == f"Charlson: {expected_name}"
            assert actual_weight == float(expected_weight)

    def test_uses_ancestor_binary_features(self):
        from circe.features.presets import charlson_index
        from circe.features.models import AncestorBinaryFeature

        feature = charlson_index()
        for comp_feature, _ in feature.components:
            assert isinstance(comp_feature, AncestorBinaryFeature)

    def test_default_domain_is_condition_era(self):
        from circe.features.presets import charlson_index

        feature = charlson_index()
        for comp_feature, _ in feature.components:
            assert comp_feature.domain == "ConditionEra"

    def test_custom_domain_and_window(self):
        from circe.features.presets import charlson_index

        feature = charlson_index(window=(-365, 0), domain="ConditionOccurrence")
        for comp_feature, _ in feature.components:
            assert comp_feature.domain == "ConditionOccurrence"
            assert comp_feature.window == (-365, 0)

    def test_concept_ids_match_r_source(self):
        """Verify specific ancestor concept IDs match the R FeatureExtraction SQL."""
        from circe.features.presets import charlson_index

        feature = charlson_index()
        components = {f.name: f for f, _ in feature.components}

        # Myocardial infarction → 4329847
        mi = components["Charlson: Myocardial infarction"]
        assert mi.ancestor_concept_ids == [4329847]

        # AIDS → 439727
        aids = components["Charlson: AIDS"]
        assert aids.ancestor_concept_ids == [439727]

        # Rheumatologic → 6 ancestor IDs
        rheum = components["Charlson: Rheumatologic disease"]
        assert len(rheum.ancestor_concept_ids) == 6
        assert 257628 in rheum.ancestor_concept_ids

    def test_composite_hash_is_deterministic(self):
        from circe.features.presets import charlson_index

        f1 = charlson_index()
        f2 = charlson_index()
        assert f1.feature_hash == f2.feature_hash
