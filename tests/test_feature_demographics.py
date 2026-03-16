"""
Tests for demographics, visit count, and era overlap feature extraction.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def demographics_ctx():
    """DuckDB BuildContext with person, visit_occurrence, and condition_era tables."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    from circe.execution.build_context import BuildContext, CohortBuildOptions, CodesetResource

    conn = ibis.duckdb.connect()

    # Person table
    conn.create_table(
        "person",
        obj=ibis.memtable({
            "person_id": [1, 2],
            "year_of_birth": [1985, 1990],
            "gender_concept_id": [8507, 8532],  # Male, Female
            "race_concept_id": [8516, 8527],     # Black, White
            "ethnicity_concept_id": [38003564, 38003563],  # Not Hispanic, Hispanic
        }),
        overwrite=True,
    )

    # Visit occurrence
    conn.create_table(
        "visit_occurrence",
        obj=ibis.memtable({
            "person_id": [1, 1, 1, 2],
            "visit_occurrence_id": [501, 502, 503, 504],
            "visit_concept_id": [9201, 9202, 9201, 9202],  # IP, OP, IP, OP
            "visit_start_date": ["2020-01-10", "2020-02-15", "2020-02-28", "2020-02-20"],
            "visit_end_date": ["2020-01-12", "2020-02-15", "2020-03-02", "2020-02-20"],
            "visit_type_concept_id": [44818517, 44818517, 44818517, 44818517],
        }),
        overwrite=True,
    )

    # Condition era
    conn.create_table(
        "condition_era",
        obj=ibis.memtable({
            "person_id": [1, 1, 2],
            "condition_era_id": [601, 602, 603],
            "condition_concept_id": [440383, 201826, 440383],
            "condition_era_start_date": ["2019-06-01", "2020-01-15", "2020-02-01"],
            "condition_era_end_date": ["2020-04-01", "2020-02-15", "2020-03-15"],
        }),
        overwrite=True,
    )

    # Drug era
    conn.create_table(
        "drug_era",
        obj=ibis.memtable({
            "person_id": [1],
            "drug_era_id": [701],
            "drug_concept_id": [1118084],
            "drug_era_start_date": ["2020-01-01"],
            "drug_era_end_date": ["2020-06-01"],
        }),
        overwrite=True,
    )

    # Vocab stubs
    conn.create_table(
        "concept",
        obj=ibis.memtable({
            "concept_id": [440383, 201826, 9201, 9202, 1118084],
            "invalid_reason": ["", "", "", "", ""],
        }),
        overwrite=True,
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable({
            "ancestor_concept_id": [440383, 201826, 9201, 9202, 1118084],
            "descendant_concept_id": [440383, 201826, 9201, 9202, 1118084],
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

    codesets_table = ibis.memtable({
        "codeset_id": [1],
        "concept_id": [440383],
    })
    resource = CodesetResource(table=codesets_table)
    options = CohortBuildOptions(materialize_stages=False, materialize_codesets=False)
    ctx = BuildContext(conn, options, resource)

    # Cohort (index date 2020-03-01)
    cohort = ibis.memtable({
        "subject_id": [1, 2],
        "cohort_start_date": ["2020-03-01", "2020-03-01"],
    })

    yield ctx, cohort, conn
    ctx.close()


# ------------------------------------------------------------------
# Demographics
# ------------------------------------------------------------------


class TestDemographicsAge:
    def test_age_computed_correctly(self, demographics_ctx):
        from circe.features import DemographicsFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = DemographicsFeature(
            include_age=True, include_gender=False,
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Person 1: born 1985, index 2020 → age 35
        # Person 2: born 1990, index 2020 → age 30
        p1 = result[result["subject_id"] == 1]["feature_value"].iloc[0]
        p2 = result[result["subject_id"] == 2]["feature_value"].iloc[0]
        assert p1 == 35.0
        assert p2 == 30.0

    def test_age_hash_uses_sub_hash(self, demographics_ctx):
        from circe.features import DemographicsFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = DemographicsFeature(
            include_age=True, include_gender=False,
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        assert result["feature_hash"].nunique() == 1
        assert result["feature_hash"].iloc[0] == feature.sub_hash("age")


class TestDemographicsGender:
    def test_gender_returns_concept_ids(self, demographics_ctx):
        from circe.features import DemographicsFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = DemographicsFeature(
            include_age=False, include_gender=True,
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Person 1: gender_concept_id 8507 (Male)
        # Person 2: gender_concept_id 8532 (Female)
        p1 = result[result["subject_id"] == 1]["feature_value"].iloc[0]
        p2 = result[result["subject_id"] == 2]["feature_value"].iloc[0]
        assert p1 == 8507.0
        assert p2 == 8532.0


class TestDemographicsIndexDate:
    def test_index_year_and_month(self, demographics_ctx):
        from circe.features import DemographicsFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = DemographicsFeature(
            include_age=False, include_gender=False,
            include_index_year=True, include_index_month=True,
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Two subjects × two sub-features (year, month) = 4 rows
        assert len(result) == 4
        year_hash = feature.sub_hash("index_year")
        month_hash = feature.sub_hash("index_month")

        year_rows = result[result["feature_hash"] == year_hash]
        month_rows = result[result["feature_hash"] == month_hash]
        assert year_rows["feature_value"].iloc[0] == 2020.0
        assert month_rows["feature_value"].iloc[0] == 3.0


class TestDemographicsNoAttributes:
    def test_no_attributes_raises(self, demographics_ctx):
        from circe.features import DemographicsFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = DemographicsFeature(
            include_age=False, include_gender=False,
        )

        extractor = FeatureExtractor(ctx, cohort)
        with pytest.raises(ValueError, match="no attributes"):
            extractor.extract_single(feature)


# ------------------------------------------------------------------
# Visit Count
# ------------------------------------------------------------------


class TestVisitCount:
    def test_visit_count_all_visits(self, demographics_ctx):
        from circe.features import VisitCountFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = VisitCountFeature(
            name="All Visits",
            window=(-90, 0),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Person 1: 3 visits (Jan 10, Feb 15, Feb 28) all within 90 days before Mar 1
        # Person 2: 1 visit (Feb 20) within 90 days before Mar 1
        p1 = result[result["subject_id"] == 1]["feature_value"].iloc[0]
        p2 = result[result["subject_id"] == 2]["feature_value"].iloc[0]
        assert p1 == 3.0
        assert p2 == 1.0

    def test_visit_count_filtered_by_type(self, demographics_ctx):
        from circe.features import VisitCountFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        # Only count inpatient visits (9201)
        feature = VisitCountFeature(
            name="Inpatient Visits",
            window=(-90, 0),
            visit_concept_ids=[9201],
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Person 1: 2 inpatient visits (Jan 10, Feb 28)
        # Person 2: 0 inpatient visits
        p1 = result[result["subject_id"] == 1]["feature_value"].iloc[0]
        p2 = result[result["subject_id"] == 2]["feature_value"].iloc[0]
        assert p1 == 2.0
        assert p2 == 0.0

    def test_visit_count_zero_for_no_visits(self, demographics_ctx):
        from circe.features import VisitCountFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        # Use a very narrow window where no visits exist
        feature = VisitCountFeature(
            name="No Visits Window",
            window=(-1, 0),  # Only Mar 1 itself
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Both subjects should have 0 visits in this 1-day window
        assert all(result["feature_value"] == 0.0)


# ------------------------------------------------------------------
# Era Overlap
# ------------------------------------------------------------------


class TestEraOverlap:
    def test_condition_era_overlap(self, demographics_ctx):
        from circe.features import EraOverlapFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = EraOverlapFeature(
            name="Condition Era Overlap",
            domain="ConditionEra",
            window=(-30, 0),  # 30 days before index (Feb 1 to Mar 1)
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Person 1: era 601 (440383, Jun 2019-Apr 2020) overlaps window
        #           era 602 (201826, Jan-Feb 2020) overlaps window
        # Person 2: era 603 (440383, Feb-Mar 2020) overlaps window
        assert len(result) >= 2
        p1_concepts = set(result[result["subject_id"] == 1]["concept_id"])
        assert 440383 in p1_concepts

    def test_era_overlap_no_match(self, demographics_ctx):
        from circe.features import EraOverlapFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = EraOverlapFeature(
            name="Drug Era Overlap",
            domain="DrugEra",
            window=(-365, -200),  # Far in the past: Sep 2019 - Aug 2019
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # Drug era starts Jan 2020; window ends at -200 days from index (~Aug 2019)
        # No overlap expected
        assert len(result) == 0


# ------------------------------------------------------------------
# Ancestor Binary
# ------------------------------------------------------------------


class TestAncestorBinary:
    def test_ancestor_binary_matches(self, demographics_ctx):
        from circe.features import AncestorBinaryFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        # Use concept_ancestor (self-referencing in test data)
        feature = AncestorBinaryFeature(
            name="Has 440383 Ancestor",
            ancestor_concept_ids=[440383],
            domain="ConditionEra",
            window=(-365, 0),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        assert len(result) == 2
        p1 = result[result["subject_id"] == 1]["feature_value"].iloc[0]
        p2 = result[result["subject_id"] == 2]["feature_value"].iloc[0]
        # Both have condition_era with concept 440383 in window
        assert p1 == 1.0
        assert p2 == 1.0

    def test_ancestor_binary_no_match(self, demographics_ctx):
        from circe.features import AncestorBinaryFeature, FeatureExtractor

        ctx, cohort, _ = demographics_ctx
        feature = AncestorBinaryFeature(
            name="Has 999999 Ancestor",
            ancestor_concept_ids=[999999],
            domain="ConditionEra",
            window=(-365, 0),
        )

        extractor = FeatureExtractor(ctx, cohort)
        result = extractor.extract_single(feature).execute()

        # No concept 999999 in concept_ancestor → all 0
        assert all(result["feature_value"] == 0.0)
