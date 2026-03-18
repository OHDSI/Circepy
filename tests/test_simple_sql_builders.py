"""
Simple tests for the new SQL builders to verify basic functionality.

GUARD RAIL: These tests ensure 1:1 compatibility with Java CIRCE-BE functionality.
Any changes must maintain compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from circe.cohortdefinition.builders import (
    BuilderOptions,
    CriteriaColumn,
    DoseEraSqlBuilder,
    LocationRegionSqlBuilder,
    ObservationPeriodSqlBuilder,
    PayerPlanPeriodSqlBuilder,
    VisitDetailSqlBuilder,
)
from circe.cohortdefinition.criteria import (
    DoseEra,
    LocationRegion,
    ObservationPeriod,
    PayerPlanPeriod,
    VisitDetail,
)


class TestBasicSqlBuilderFunctionality:
    """Test basic functionality of all SQL builders."""

    def test_dose_era_sql_builder_basic(self):
        """Test basic DoseEraSqlBuilder functionality."""
        builder = DoseEraSqlBuilder()
        DoseEra(first=False)

        # Test basic methods
        assert isinstance(builder.get_query_template(), str)
        assert isinstance(builder.get_default_columns(), set)
        assert "DOSE_ERA" in builder.get_query_template()

        # Test column mapping
        assert (
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT) == "C.drug_concept_id"
        )
        assert (
            builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION)
            == "DATEDIFF(d, C.start_date, C.end_date)"
        )

    def test_observation_period_sql_builder_basic(self):
        """Test basic ObservationPeriodSqlBuilder functionality."""
        builder = ObservationPeriodSqlBuilder()
        ObservationPeriod()

        # Test basic methods
        assert isinstance(builder.get_query_template(), str)
        assert isinstance(builder.get_default_columns(), set)
        assert "OBSERVATION_PERIOD" in builder.get_query_template()

        # Test column mapping
        assert (
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT)
            == "C.period_type_concept_id"
        )

    def test_payer_plan_period_sql_builder_basic(self):
        """Test basic PayerPlanPeriodSqlBuilder functionality."""
        builder = PayerPlanPeriodSqlBuilder()
        PayerPlanPeriod()

        # Test basic methods
        assert isinstance(builder.get_query_template(), str)
        assert isinstance(builder.get_default_columns(), set)
        assert "PAYER_PLAN_PERIOD" in builder.get_query_template()

        # Test column mapping
        assert (
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT)
            == "C.payer_concept_id"
        )

    def test_visit_detail_sql_builder_basic(self):
        """Test basic VisitDetailSqlBuilder functionality."""
        builder = VisitDetailSqlBuilder()
        VisitDetail(visit_detail_type_exclude=False)

        # Test basic methods
        assert isinstance(builder.get_query_template(), str)
        assert isinstance(builder.get_default_columns(), set)
        assert "VISIT_DETAIL" in builder.get_query_template()

        # Test column mapping
        assert (
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT)
            == "C.visit_detail_concept_id"
        )
        assert (
            builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_DETAIL_ID)
            == "C.visit_detail_id"
        )

    def test_location_region_sql_builder_basic(self):
        """Test basic LocationRegionSqlBuilder functionality."""
        builder = LocationRegionSqlBuilder()
        LocationRegion()

        # Test basic methods
        assert isinstance(builder.get_query_template(), str)
        assert isinstance(builder.get_default_columns(), set)
        assert "LOCATION" in builder.get_query_template()

        # Test column mapping
        assert (
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT)
            == "C.region_concept_id"
        )

    def test_all_builders_have_required_methods(self):
        """Test that all builders implement required methods."""
        builders = [
            DoseEraSqlBuilder(),
            ObservationPeriodSqlBuilder(),
            PayerPlanPeriodSqlBuilder(),
            VisitDetailSqlBuilder(),
            LocationRegionSqlBuilder(),
        ]

        for builder in builders:
            # Test required abstract methods
            assert hasattr(builder, "get_query_template")
            assert hasattr(builder, "get_default_columns")
            assert hasattr(builder, "get_table_column_for_criteria_column")
            assert hasattr(builder, "embed_codeset_clause")
            assert hasattr(builder, "embed_ordinal_expression")
            assert hasattr(builder, "resolve_select_clauses")
            assert hasattr(builder, "resolve_join_clauses")
            assert hasattr(builder, "resolve_where_clauses")

            # Test that methods are callable
            assert callable(builder.get_query_template)
            assert callable(builder.get_default_columns)
            assert callable(builder.get_table_column_for_criteria_column)

    def test_builder_inheritance(self):
        """Test that all builders inherit from CriteriaSqlBuilder."""
        from circe.cohortdefinition.builders.base import CriteriaSqlBuilder

        builders = [
            DoseEraSqlBuilder(),
            ObservationPeriodSqlBuilder(),
            PayerPlanPeriodSqlBuilder(),
            VisitDetailSqlBuilder(),
            LocationRegionSqlBuilder(),
        ]

        for builder in builders:
            assert isinstance(builder, CriteriaSqlBuilder)

    def test_criteria_column_enum(self):
        """Test that CriteriaColumn enum has all required values."""
        required_columns = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID,
            CriteriaColumn.VISIT_DETAIL_ID,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.DURATION,
            CriteriaColumn.UNIT,
            CriteriaColumn.VALUE_AS_NUMBER,
        }

        for column in required_columns:
            assert column in CriteriaColumn

    def test_builder_options(self):
        """Test BuilderOptions functionality."""
        options = BuilderOptions()
        assert isinstance(options.additional_columns, list)

        options.additional_columns = [
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
        ]
        assert len(options.additional_columns) == 2
        assert CriteriaColumn.START_DATE in options.additional_columns
        assert CriteriaColumn.END_DATE in options.additional_columns
