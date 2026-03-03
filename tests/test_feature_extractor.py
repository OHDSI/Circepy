"""
Unit tests for circe.features.extractor — feature extraction engine.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def feature_ctx():
    """Create DuckDB-backed BuildContext with condition_occurrence and measurement data."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    from circe.execution.build_context import BuildContext, CohortBuildOptions, CodesetResource

    conn = ibis.duckdb.connect()

    # Condition occurrence (two patients, multiple concepts)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable({
            "person_id": [1, 1, 1, 2, 2],
            "condition_occurrence_id": [101, 102, 103, 104, 105],
            "condition_concept_id": [440383, 440383, 201826, 440383, 201826],
            "condition_start_date": [
                "2020-01-15", "2020-02-20", "2020-06-01",
                "2020-03-10", "2020-04-15",
            ],
            "condition_end_date": [
                "2020-01-20", "2020-02-25", "2020-06-05",
                "2020-03-15", "2020-04-20",
            ],
            "condition_type_concept_id": [32817, 32817, 32817, 32817, 32817],
            "condition_status_concept_id": [0, 0, 0, 0, 0],
            "visit_occurrence_id": [1001, 1002, 1003, 1004, 1005],
        }),
        overwrite=True,
    )

    # Measurement (BMI values)
    conn.create_table(
        "measurement",
        obj=ibis.memtable({
            "person_id": [1, 1, 2],
            "measurement_id": [201, 202, 203],
            "measurement_concept_id": [3038553, 3038553, 3038553],
            "measurement_date": ["2020-02-01", "2020-04-01", "2020-03-15"],
            "value_as_number": [28.5, 29.1, 24.3],
            "value_as_concept_id": [0, 0, 0],
            "range_low": [18.5, 18.5, 18.5],
            "range_high": [30.0, 30.0, 30.0],
            "measurement_type_concept_id": [32817, 32817, 32817],
            "unit_concept_id": [9529, 9529, 9529],
            "operator_concept_id": [0, 0, 0],
            "visit_occurrence_id": [1001, 1002, 1003],
        }),
        overwrite=True,
    )

    # Vocab tables
    conn.create_table(
        "concept",
        obj=ibis.memtable({
            "concept_id": [440383, 201826, 3038553],
            "invalid_reason": ["", "", ""],
        }),
        overwrite=True,
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable({
            "ancestor_concept_id": [440383, 201826, 3038553],
            "descendant_concept_id": [440383, 201826, 3038553],
        }),
        overwrite=True,
    )
    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable({
            "concept_id_1": [440383],
            "concept_id_2": [440383],
            "relationship_id": ["Maps to"],
            "invalid_reason": [""],
        }),
        overwrite=True,
    )

    # Codesets: codeset_id=1 has concept 440383, codeset_id=2 has 3038553
    codesets_table = ibis.memtable({
        "codeset_id": [1, 2],
        "concept_id": [440383, 3038553],
    })
    resource = CodesetResource(table=codesets_table)
    options = CohortBuildOptions(materialize_stages=False, materialize_codesets=False)
    ctx = BuildContext(conn, options, resource)

    # Cohort table (both patients with index date 2020-03-01)
    cohort = ibis.memtable({
        "subject_id": [1, 2],
        "cohort_start_date": ["2020-03-01", "2020-03-01"],
    })

    yield ctx, cohort, conn
    ctx.close()


class TestBinaryExtraction:
    def test_binary_feature_returns_0_and_1(self, feature_ctx):
        from circe.features import BinaryFeature, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        feature = BinaryFeature(
            name="Has Condition 440383",
            codeset_id=1,
            domain="ConditionOccurrence",
            window=(-90, 0),  # 90 days before index
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        assert len(result) == 2
        assert "feature_value" in result.columns
        assert "feature_hash" in result.columns
        # Person 1 has 440383 on Jan 15 (-46 days) and Feb 20 (-10 days) → 1
        # Person 2 has 440383 on Mar 10 (+9 days) → outside window → 0
        person_1 = result[result["subject_id"] == 1]["feature_value"].iloc[0]
        person_2 = result[result["subject_id"] == 2]["feature_value"].iloc[0]
        assert person_1 == 1.0
        assert person_2 == 0.0

    def test_binary_feature_hash_is_consistent(self, feature_ctx):
        from circe.features import BinaryFeature, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        feature = BinaryFeature(
            name="Has Condition", codeset_id=1,
            domain="ConditionOccurrence", window=(-90, 0),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        assert result["feature_hash"].nunique() == 1
        assert result["feature_hash"].iloc[0] == feature.feature_hash


class TestValueExtraction:
    def test_count_aggregation(self, feature_ctx):
        from circe.features import Aggregation, ValueFeature, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        feature = ValueFeature(
            name="Condition Count",
            codeset_id=1,
            domain="ConditionOccurrence",
            value_column="condition_concept_id",
            aggregation=Aggregation.COUNT,
            window=(-90, 0),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Person 1: concepts 440383 on Jan 15 and Feb 20 → count=2
        # Person 2: no 440383 events in window → no rows
        person_1 = result[result["subject_id"] == 1]
        assert len(person_1) == 1
        assert person_1["feature_value"].iloc[0] == 2

    def test_avg_aggregation(self, feature_ctx):
        from circe.features import Aggregation, ValueFeature, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        feature = ValueFeature(
            name="Avg BMI",
            codeset_id=2,
            domain="Measurement",
            value_column="value_as_number",
            aggregation=Aggregation.AVG,
            window=(-90, 0),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Person 1: BMI 28.5 on Feb 1 → avg=28.5
        # Person 2: BMI 24.3 on Mar 15 → +14 days, outside (0, 0] window? Actually window is -90 to 0
        person_1 = result[result["subject_id"] == 1]
        assert len(person_1) >= 1
        assert abs(person_1["feature_value"].iloc[0] - 28.5) < 0.1

    def test_latest_aggregation(self, feature_ctx):
        from circe.features import Aggregation, ValueFeature, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        feature = ValueFeature(
            name="Latest BMI",
            codeset_id=2,
            domain="Measurement",
            value_column="value_as_number",
            aggregation=Aggregation.LATEST,
            window=(-365, 365),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Person 1 has BMI on Feb 1 and Apr 1. Latest = Apr 1 (29.1)
        person_1 = result[result["subject_id"] == 1]
        assert len(person_1) == 1
        assert abs(person_1["feature_value"].iloc[0] - 29.1) < 0.1

    def test_missing_column_raises(self, feature_ctx):
        from circe.features import Aggregation, ValueFeature, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        feature = ValueFeature(
            name="Bad Column",
            codeset_id=1,
            domain="ConditionOccurrence",
            value_column="nonexistent_column",
            aggregation=Aggregation.AVG,
            window=(-90, 0),
        )

        extractor = FeatureExtractor(ctx, cohort)
        with pytest.raises(ValueError, match="not found"):
            extractor.extract_single(feature).execute()


class TestCompositeExtraction:
    def test_weighted_sum(self, feature_ctx):
        from circe.features import (
            BinaryFeature, CompositeFeature, FeatureExtractor,
        )

        ctx, cohort, _ = feature_ctx

        comp1 = BinaryFeature(
            name="Has 440383", codeset_id=1,
            domain="ConditionOccurrence", window=(-365, 0),
        )
        comp2 = BinaryFeature(
            name="Has 440383 (wide)", codeset_id=1,
            domain="ConditionOccurrence", window=(-365, 365),
        )

        composite = CompositeFeature(
            name="Weighted Score",
            components=[(comp1, 2.0), (comp2, 3.0)],
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(composite).execute()

        # Person 1: comp1=1 (has events before), comp2=1 (has events in wide window)
        # → 1*2 + 1*3 = 5.0
        person_1 = result[result["subject_id"] == 1]
        assert len(person_1) == 1
        assert person_1["feature_value"].iloc[0] == 5.0


class TestBulkExtraction:
    def test_bulk_returns_per_concept_rows(self, feature_ctx):
        from circe.features import BulkDomainFeature, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        feature = BulkDomainFeature(
            name="All Conditions",
            domain="ConditionOccurrence",
            window=(-365, 365),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        assert "concept_id" in result.columns
        assert "feature_value" in result.columns
        # Should have rows for both concept_ids (440383, 201826) 
        concepts = set(result["concept_id"].unique())
        assert 440383 in concepts


class TestTemporalSequences:
    def test_sequence_extraction(self, feature_ctx):
        from circe.features import TemporalConfig, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        config = TemporalConfig(
            domains=["ConditionOccurrence", "Measurement"],
            window=(-365, 365),
            include_values=True,
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_sequences(config).execute()

        assert "subject_id" in result.columns
        assert "time_delta_days" in result.columns
        assert "concept_id" in result.columns
        assert "domain" in result.columns
        assert "value" in result.columns
        # Should have events from both domains
        domains = set(result["domain"].unique())
        assert "ConditionOccurrence" in domains
        assert "Measurement" in domains

    def test_sequence_sorted_by_time(self, feature_ctx):
        from circe.features import TemporalConfig, FeatureExtractor

        ctx, cohort, _ = feature_ctx

        config = TemporalConfig(
            domains=["ConditionOccurrence"],
            window=(-365, 365),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_sequences(config).execute()

        # Check events are sorted by time within each subject
        for _, group in result.groupby("subject_id"):
            deltas = list(group["time_delta_days"])
            assert deltas == sorted(deltas)


class TestFeatureSetExtraction:
    def test_extract_full_set(self, feature_ctx):
        from circe.features import (
            BinaryFeature, ValueFeature, Aggregation,
            FeatureSet, TemporalConfig, FeatureExtractor,
        )

        ctx, cohort, _ = feature_ctx

        fs = FeatureSet(name="Test Feature Set")
        fs.add(BinaryFeature(
            name="Has 440383", codeset_id=1,
            domain="ConditionOccurrence", window=(-365, 0),
        ))
        fs.add(ValueFeature(
            name="BMI Count", codeset_id=2,
            domain="Measurement", value_column="value_as_number",
            aggregation=Aggregation.COUNT, window=(-365, 365),
        ))
        fs.temporal = TemporalConfig(
            domains=["ConditionOccurrence"],
            window=(-365, 365),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract(fs)

        assert result.scalar is not None
        assert result.temporal is not None

        scalar_df = result.scalar.execute()
        assert "feature_hash" in scalar_df.columns
        assert scalar_df["feature_hash"].nunique() == 2  # Two features

        temporal_df = result.temporal.execute()
        assert len(temporal_df) > 0

    def test_feature_result_repr(self, feature_ctx):
        from circe.features.extractor import FeatureResult
        r = FeatureResult()
        assert "FeatureResult" in repr(r)
