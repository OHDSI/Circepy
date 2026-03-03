"""
Unit tests for Phase 4: FeatureSetBuilder and table_one summary.
"""

from __future__ import annotations

import pytest
import pandas as pd


@pytest.fixture
def feature_ctx_simple():
    """Simple DuckDB context for builder tests."""
    ibis = pytest.importorskip("ibis")
    from circe.execution.build_context import (
        BuildContext, CohortBuildOptions, CodesetResource
    )

    conn = ibis.duckdb.connect()
    
    # Minimal tables
    conn.create_table("condition_occurrence", obj=ibis.memtable({
        "person_id": [1], "condition_concept_id": [440383],
        "condition_start_date": ["2020-01-01"], "condition_end_date": ["2020-01-01"],
        "visit_occurrence_id": [1], "condition_occurrence_id": [1]
    }))
    conn.create_table("measurement", obj=ibis.memtable({
        "person_id": [1], "measurement_concept_id": [3038553],
        "measurement_date": ["2020-01-01"], "value_as_number": [25.0],
        "visit_occurrence_id": [1], "measurement_id": [1]
    }))
    
    # Vocab
    conn.create_table("concept", obj=ibis.memtable({"concept_id": [440383, 3038553], "invalid_reason": ["", ""]}))
    conn.create_table("concept_ancestor", obj=ibis.memtable({"ancestor_concept_id": [440383, 3038553], "descendant_concept_id": [440383, 3038553]}))

    codesets = ibis.memtable({"codeset_id": [1, 2], "concept_id": [440383, 3038553]})
    ctx = BuildContext(conn, CohortBuildOptions(), CodesetResource(table=codesets))
    
    cohort = ibis.memtable({"subject_id": [1, 2], "cohort_start_date": ["2020-01-02", "2020-01-02"]})
    
    return ctx, cohort


class TestFeatureSetBuilder:
    def test_builder_fluent_api(self):
        from circe.features import FeatureSetBuilder, Aggregation
        
        builder = FeatureSetBuilder("My Set")
        builder.binary("Diabetes", codeset_id=1)
        builder.value("BMI", codeset_id=2, value_column="value_as_number", aggregation="avg")
        builder.bulk("Measurement", window=(-365, 365))
        builder.temporal(["ConditionOccurrence"], window=(-30, 30))
        
        fs = builder.build()
        
        assert fs.name == "My Set"
        assert len(fs) == 3
        assert fs.temporal is not None
        assert fs.temporal.domains == ["ConditionOccurrence"]
        
        # Check types
        features = list(fs)
        assert any(f.name == "Diabetes" and f.feature_type == "binary" for f in features)
        assert any(f.name == "BMI" and f.aggregation == Aggregation.AVG for f in features)
        assert any("Bulk Measurement" in f.name for f in features)

    def test_builder_returns_self(self):
        from circe.features import FeatureSetBuilder
        b = FeatureSetBuilder()
        assert b.binary("X", 1) is b
        assert b.value("Y", 2, "v") is b
        assert b.bulk("Z") is b
        assert b.temporal(["T"]) is b


class TestTableOne:
    def test_table_one_summary(self, feature_ctx_simple):
        from circe.features import (
            FeatureSetBuilder, FeatureExtractor, table_one
        )
        
        ctx, cohort = feature_ctx_simple
        
        builder = FeatureSetBuilder("Table 1 Test")
        builder.binary("Has Diabetes", codeset_id=1, window=(-365, 365))
        builder.value("Avg BMI", codeset_id=2, value_column="value_as_number", aggregation="avg", window=(-365, 365))
        
        fs = builder.build()
        extractor = FeatureExtractor(ctx, cohort)
        results = extractor.extract(fs)
        
        summary = table_one(results, fs)
        
        assert isinstance(summary, pd.DataFrame)
        assert len(summary) == 2
        assert "Feature" in summary.columns
        assert "Summary" in summary.columns
        
        # Person 1 has both, Person 2 has neither (Total N=2)
        # Diabetes: 1 (50.0%)
        diabetes_row = summary[summary["Feature"] == "Has Diabetes"].iloc[0]
        assert "1 (50.0%)" in diabetes_row["Summary"]
        
        # BMI: mean 25.0
        bmi_row = summary[summary["Feature"] == "Avg BMI"].iloc[0]
        assert "25.00" in bmi_row["Summary"]

    def test_table_one_empty(self):
        from circe.features import table_one, FeatureResult, FeatureSet
        res = FeatureResult(scalar=None)
        fs = FeatureSet(name="Empty")
        summary = table_one(res, fs)
        assert summary.empty
