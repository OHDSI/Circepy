"""
Unit tests for circe.features.models — feature definitions and hashing.
"""

import pytest

from circe.features.models import (
    Aggregation,
    BinaryFeature,
    BulkDomainFeature,
    CompositeFeature,
    FeatureSet,
    FeatureType,
    TemporalConfig,
    ValueFeature,
)


class TestBinaryFeature:
    def test_hash_determinism(self):
        """Same inputs must always produce the same hash."""
        f1 = BinaryFeature("GI Bleed", codeset_id=1, domain="ConditionOccurrence", window=(-30, 0))
        f2 = BinaryFeature("GI Bleed", codeset_id=1, domain="ConditionOccurrence", window=(-30, 0))
        assert f1.feature_hash == f2.feature_hash

    def test_different_name_same_hash(self):
        """Hash is based on domain+codeset+window, not name."""
        f1 = BinaryFeature("GI Bleed", codeset_id=1, domain="ConditionOccurrence", window=(-30, 0))
        f2 = BinaryFeature("Different Name", codeset_id=1, domain="ConditionOccurrence", window=(-30, 0))
        assert f1.feature_hash == f2.feature_hash

    def test_different_window_different_hash(self):
        f1 = BinaryFeature("GI Bleed", codeset_id=1, domain="ConditionOccurrence", window=(-30, 0))
        f2 = BinaryFeature("GI Bleed", codeset_id=1, domain="ConditionOccurrence", window=(-365, 0))
        assert f1.feature_hash != f2.feature_hash

    def test_different_codeset_different_hash(self):
        f1 = BinaryFeature("GI Bleed", codeset_id=1, domain="ConditionOccurrence")
        f2 = BinaryFeature("GI Bleed", codeset_id=2, domain="ConditionOccurrence")
        assert f1.feature_hash != f2.feature_hash

    def test_feature_type(self):
        f = BinaryFeature("x", codeset_id=1, domain="ConditionOccurrence")
        assert f.feature_type == FeatureType.BINARY

    def test_repr(self):
        f = BinaryFeature("GI Bleed", codeset_id=1, domain="ConditionOccurrence")
        r = repr(f)
        assert "BinaryFeature" in r
        assert "GI Bleed" in r

    def test_to_dict(self):
        f = BinaryFeature("GI Bleed", codeset_id=1, domain="ConditionOccurrence", description="Test")
        d = f.to_dict()
        assert d["feature_name"] == "GI Bleed"
        assert d["feature_type"] == "binary"
        assert d["feature_hash"] == f.feature_hash
        assert d["description"] == "Test"

    def test_equality(self):
        f1 = BinaryFeature("A", codeset_id=1, domain="ConditionOccurrence", window=(-30, 0))
        f2 = BinaryFeature("B", codeset_id=1, domain="ConditionOccurrence", window=(-30, 0))
        assert f1 == f2  # Same hash → equal
        f3 = BinaryFeature("A", codeset_id=2, domain="ConditionOccurrence", window=(-30, 0))
        assert f1 != f3

    def test_hashable(self):
        """Feature definitions can be used in sets and as dict keys."""
        f1 = BinaryFeature("A", codeset_id=1, domain="ConditionOccurrence")
        f2 = BinaryFeature("B", codeset_id=1, domain="ConditionOccurrence")
        s = {f1, f2}
        assert len(s) == 1  # Same hash → deduplicated

    def test_with_criteria_json(self):
        criteria = {"Type": "ALL", "CriteriaList": []}
        f1 = BinaryFeature("A", codeset_id=1, domain="ConditionOccurrence", criteria_json=criteria)
        f2 = BinaryFeature("A", codeset_id=1, domain="ConditionOccurrence")
        assert f1.feature_hash != f2.feature_hash


class TestValueFeature:
    def test_hash_determinism(self):
        f1 = ValueFeature("BMI", codeset_id=5, domain="Measurement", aggregation=Aggregation.LATEST)
        f2 = ValueFeature("BMI", codeset_id=5, domain="Measurement", aggregation=Aggregation.LATEST)
        assert f1.feature_hash == f2.feature_hash

    def test_different_aggregation_different_hash(self):
        f1 = ValueFeature("BMI", codeset_id=5, domain="Measurement", aggregation=Aggregation.LATEST)
        f2 = ValueFeature("BMI", codeset_id=5, domain="Measurement", aggregation=Aggregation.AVG)
        assert f1.feature_hash != f2.feature_hash

    def test_different_column_different_hash(self):
        f1 = ValueFeature("Lab", codeset_id=5, domain="Measurement", value_column="value_as_number")
        f2 = ValueFeature("Lab", codeset_id=5, domain="Measurement", value_column="range_low")
        assert f1.feature_hash != f2.feature_hash

    def test_feature_type(self):
        f = ValueFeature("x", codeset_id=1, domain="Measurement")
        assert f.feature_type == FeatureType.VALUE


class TestCompositeFeature:
    def test_hash_from_components(self):
        c1 = BinaryFeature("MI", codeset_id=1, domain="ConditionOccurrence", window=(-365, 0))
        c2 = BinaryFeature("CHF", codeset_id=2, domain="ConditionOccurrence", window=(-365, 0))
        comp = CompositeFeature("Charlson", components=[(c1, 1.0), (c2, 1.0)])
        assert comp.feature_type == FeatureType.COMPOSITE
        assert len(comp.component_hashes) == 2

    def test_hash_determinism(self):
        c1 = BinaryFeature("MI", codeset_id=1, domain="ConditionOccurrence")
        c2 = BinaryFeature("CHF", codeset_id=2, domain="ConditionOccurrence")
        comp_a = CompositeFeature("Charlson", components=[(c1, 1.0), (c2, 2.0)])
        comp_b = CompositeFeature("Charlson", components=[(c1, 1.0), (c2, 2.0)])
        assert comp_a.feature_hash == comp_b.feature_hash

    def test_different_weights_different_hash(self):
        c1 = BinaryFeature("MI", codeset_id=1, domain="ConditionOccurrence")
        comp_a = CompositeFeature("A", components=[(c1, 1.0)])
        comp_b = CompositeFeature("B", components=[(c1, 2.0)])
        assert comp_a.feature_hash != comp_b.feature_hash


class TestBulkDomainFeature:
    def test_basics(self):
        f = BulkDomainFeature("Conditions_365d", domain="ConditionOccurrence", window=(-365, 0))
        assert f.feature_type == FeatureType.BULK_DOMAIN
        assert f.domain == "ConditionOccurrence"

    def test_hash_determinism(self):
        f1 = BulkDomainFeature("x", domain="ConditionOccurrence", window=(-365, 0))
        f2 = BulkDomainFeature("y", domain="ConditionOccurrence", window=(-365, 0))
        assert f1.feature_hash == f2.feature_hash

    def test_ancestor_flag_changes_hash(self):
        f1 = BulkDomainFeature("x", domain="ConditionOccurrence", use_ancestors=False)
        f2 = BulkDomainFeature("x", domain="ConditionOccurrence", use_ancestors=True)
        assert f1.feature_hash != f2.feature_hash


class TestTemporalConfig:
    def test_cache_key_determinism(self):
        t1 = TemporalConfig(domains=["ConditionOccurrence", "DrugExposure"], window=(-365, 0))
        t2 = TemporalConfig(domains=["DrugExposure", "ConditionOccurrence"], window=(-365, 0))
        # Domains are sorted internally, so order shouldn't matter
        assert t1.cache_key == t2.cache_key

    def test_different_window_different_key(self):
        t1 = TemporalConfig(domains=["ConditionOccurrence"], window=(-365, 0))
        t2 = TemporalConfig(domains=["ConditionOccurrence"], window=(-180, 0))
        assert t1.cache_key != t2.cache_key

    def test_repr(self):
        t = TemporalConfig(domains=["ConditionOccurrence"], window=(-365, 0))
        assert "TemporalConfig" in repr(t)


class TestFeatureSet:
    def test_add_and_iterate(self):
        fs = FeatureSet("Table 1")
        f1 = BinaryFeature("A", codeset_id=1, domain="ConditionOccurrence")
        f2 = ValueFeature("BMI", codeset_id=2, domain="Measurement")
        fs.add(f1).add(f2)
        assert len(fs) == 2
        assert list(fs) == [f1, f2]

    def test_feature_hashes_dedup(self):
        f1 = BinaryFeature("A", codeset_id=1, domain="ConditionOccurrence")
        f2 = BinaryFeature("B", codeset_id=1, domain="ConditionOccurrence")  # Same hash
        fs = FeatureSet("test", features=[f1, f2])
        assert len(fs.feature_hashes) == 1

    def test_features_by_type(self):
        f1 = BinaryFeature("A", codeset_id=1, domain="ConditionOccurrence")
        f2 = ValueFeature("BMI", codeset_id=2, domain="Measurement")
        f3 = BinaryFeature("B", codeset_id=3, domain="DrugExposure")
        fs = FeatureSet("test", features=[f1, f2, f3])
        by_type = fs.features_by_type
        assert len(by_type[FeatureType.BINARY]) == 2
        assert len(by_type[FeatureType.VALUE]) == 1

    def test_with_temporal(self):
        tc = TemporalConfig(domains=["ConditionOccurrence"], window=(-365, 0))
        fs = FeatureSet("test", temporal=tc)
        assert fs.temporal is not None
        assert "yes" in repr(fs)

    def test_repr(self):
        fs = FeatureSet("My Features")
        assert "My Features" in repr(fs)
        assert "features=0" in repr(fs)
