"""
Tests for the new SQL builders: DoseEraSqlBuilder, ObservationPeriodSqlBuilder, 
PayerPlanPeriodSqlBuilder, VisitDetailSqlBuilder, LocationRegionSqlBuilder

GUARD RAIL: These tests ensure 1:1 compatibility with Java CIRCE-BE functionality.
Any changes must maintain compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

import pytest
from unittest.mock import Mock
from circe.cohortdefinition.builders import (
    DoseEraSqlBuilder, ObservationPeriodSqlBuilder, PayerPlanPeriodSqlBuilder,
    VisitDetailSqlBuilder, LocationRegionSqlBuilder, BuilderOptions, CriteriaColumn
)
from circe.cohortdefinition.criteria import (
    DoseEra, ObservationPeriod, PayerPlanPeriod, VisitDetail, LocationRegion
)
from circe.cohortdefinition.core import DateRange, NumericRange, ConceptSetSelection
from circe.vocabulary.concept import Concept


class TestDoseEraSqlBuilder:
    """Test DoseEraSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = DoseEraSqlBuilder()
        template = builder.get_query_template()
        
        assert "@selectClause" in template
        assert "@codesetClause" in template
        assert "@joinClause" in template
        assert "@whereClause" in template
        assert "@ordinalExpression" in template
        assert "@additionalColumns" in template
        assert "DOSE_ERA" in template
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = DoseEraSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        assert default_cols == expected_cols
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = DoseEraSqlBuilder()
        
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT) == "C.drug_concept_id"
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION) == "DATEDIFF(d, C.start_date, C.end_date)"
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.UNIT) == "C.unit_concept_id"
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.VALUE_AS_NUMBER) == "C.dose_value"
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False, codeset_id=123)
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        assert "@codesetClause" not in result
        assert "codeset_id = 123" in result
    
    def test_embed_codeset_clause_no_codeset(self):
        """Test codeset clause embedding with no codeset."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        assert "@codesetClause" not in result
        assert result == "SELECT * FROM table "
    
    def test_embed_ordinal_expression_first(self):
        """Test ordinal expression with first=True."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=True)
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert "row_number()" in result
        assert "C.ordinal = 1" in where_clauses
    
    def test_embed_ordinal_expression_not_first(self):
        """Test ordinal expression with first=False."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert "row_number()" not in result
        assert len(where_clauses) == 0
    
    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        assert "de.person_id" in select_clauses
        assert "de.dose_era_id" in select_clauses
        assert "de.drug_concept_id" in select_clauses
        assert "de.unit_concept_id" in select_clauses
        assert "de.dose_value" in select_clauses
        assert "de.dose_era_start_date as start_date" in " ".join(select_clauses)
        assert "de.dose_era_end_date as end_date" in " ".join(select_clauses)
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 0
    
    def test_resolve_join_clauses_with_person(self):
        """Test join clauses resolution with person join."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False, age_at_start=NumericRange(op=">=", value=18))
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 1
        assert "PERSON P" in join_clauses[0]
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) == 0
    
    def test_resolve_where_clauses_with_filters(self):
        """Test where clauses resolution with filters."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(
            first=False,
            era_start_date=DateRange(op=">=", value="2020-01-01"),
            dose_value=NumericRange(op=">", value=100)
        )
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) >= 2
        assert any("C.start_date" in clause for clause in where_clauses)
        assert any("C.dose_value" in clause for clause in where_clauses)


class TestObservationPeriodSqlBuilder:
    """Test ObservationPeriodSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = ObservationPeriodSqlBuilder()
        template = builder.get_query_template()
        
        assert "@selectClause" in template
        assert "@codesetClause" in template
        assert "@joinClause" in template
        assert "@whereClause" in template
        assert "@ordinalExpression" in template
        assert "@additionalColumns" in template
        assert "OBSERVATION_PERIOD" in template
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = ObservationPeriodSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        assert default_cols == expected_cols
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = ObservationPeriodSqlBuilder()
        
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT) == "C.period_type_concept_id"
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION) == "DATEDIFF(d, @startDateExpression, @endDateExpression)"
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        assert "@codesetClause" not in result
        assert result == "SELECT * FROM table "
    
    def test_embed_ordinal_expression(self):
        """Test ordinal expression embedding."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert len(where_clauses) == 0
    
    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        assert "op.person_id" in select_clauses
        assert "op.observation_period_id" in select_clauses
        assert "op.period_type_concept_id" in select_clauses
        assert "op.observation_period_start_date as start_date" in " ".join(select_clauses)
        assert "op.observation_period_end_date as end_date" in " ".join(select_clauses)
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 0
    
    def test_resolve_join_clauses_with_person(self):
        """Test join clauses resolution with person join."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod(age=NumericRange(op=">=", value=18))
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 1
        assert "PERSON P" in join_clauses[0]
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) == 0
    
    def test_resolve_where_clauses_with_filters(self):
        """Test where clauses resolution with filters."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod(
            occurrence_start_date=DateRange(op=">=", value="2020-01-01"),
            age=NumericRange(op=">", value=30)
        )
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) >= 1
        assert any("C.start_date" in clause for clause in where_clauses)


class TestPayerPlanPeriodSqlBuilder:
    """Test PayerPlanPeriodSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = PayerPlanPeriodSqlBuilder()
        template = builder.get_query_template()
        
        assert "@selectClause" in template
        assert "@codesetClause" in template
        assert "@joinClause" in template
        assert "@whereClause" in template
        assert "@ordinalExpression" in template
        assert "@additionalColumns" in template
        assert "PAYER_PLAN_PERIOD" in template
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = PayerPlanPeriodSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        assert default_cols == expected_cols
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = PayerPlanPeriodSqlBuilder()
        
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT) == "C.payer_concept_id"
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        assert "@codesetClause" not in result
        assert result == "SELECT * FROM table "
    
    def test_embed_ordinal_expression(self):
        """Test ordinal expression embedding."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert len(where_clauses) == 0
    
    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        assert "ppp.person_id" in select_clauses
        assert "ppp.payer_plan_period_id" in select_clauses
        assert "ppp.payer_plan_period_start_date as start_date" in " ".join(select_clauses)
        assert "ppp.payer_plan_period_end_date as end_date" in " ".join(select_clauses)
    
    def test_resolve_select_clauses_with_concepts(self):
        """Test select clauses resolution with concept fields."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod(
            payer_source_concept=123,
            plan_source_concept=456,
            sponsor_source_concept=789
        )
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        assert "ppp.payer_source_concept_id" in select_clauses
        assert "ppp.plan_source_concept_id" in select_clauses
        assert "ppp.sponsor_source_concept_id" in select_clauses
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 0
    
    def test_resolve_join_clauses_with_person(self):
        """Test join clauses resolution with person join."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod(age=NumericRange(op=">=", value=18))
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 1
        assert "PERSON P" in join_clauses[0]
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) == 0
    
    def test_resolve_where_clauses_with_filters(self):
        """Test where clauses resolution with filters."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod(
            occurrence_start_date=DateRange(op=">=", value="2020-01-01"),
            payer_source_concept=123
        )
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) >= 2
        assert any("C.start_date" in clause for clause in where_clauses)
        assert any("payer_source_concept_id" in clause for clause in where_clauses)


class TestVisitDetailSqlBuilder:
    """Test VisitDetailSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = VisitDetailSqlBuilder()
        template = builder.get_query_template()
        
        assert "@selectClause" in template
        assert "@codesetClause" in template
        assert "@joinClause" in template
        assert "@whereClause" in template
        assert "@ordinalExpression" in template
        assert "@additionalColumns" in template
        assert "VISIT_DETAIL" in template
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = VisitDetailSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_DETAIL_ID}
        assert default_cols == expected_cols
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = VisitDetailSqlBuilder()
        
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT) == "C.visit_detail_concept_id"
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION) == "DATEDIFF(d, C.start_date, C.end_date)"
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_DETAIL_ID) == "C.visit_detail_id"
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False, codeset_id=123)
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        assert "@codesetClause" not in result
        assert "Codesets" in result
    
    def test_embed_ordinal_expression_first(self):
        """Test ordinal expression with first=True."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False, first=True)
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert "row_number()" in result
        assert "C.ordinal = 1" in where_clauses
    
    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False)
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        assert "vd.person_id" in select_clauses
        assert "vd.visit_detail_id" in select_clauses
        assert "vd.visit_detail_concept_id" in select_clauses
        assert "vd.visit_occurrence_id" in select_clauses
        assert "vd.visit_detail_start_date as start_date" in " ".join(select_clauses)
        assert "vd.visit_detail_end_date as end_date" in " ".join(select_clauses)
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False)
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 0
    
    def test_resolve_join_clauses_with_person(self):
        """Test join clauses resolution with person join."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False, age=NumericRange(op=">=", value=18))
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 1
        assert "PERSON P" in join_clauses[0]
    
    def test_resolve_join_clauses_with_care_site(self):
        """Test join clauses resolution with care site join."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(
            visit_detail_type_exclude=False, 
            place_of_service_cs=ConceptSetSelection(codeset_id=123, is_exclusion=False)
        )
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 1
        assert "CARE_SITE CS" in join_clauses[0]
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False)
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) == 0
    
    def test_resolve_where_clauses_with_filters(self):
        """Test where clauses resolution with filters."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(
            visit_detail_type_exclude=False,
            occurrence_start_date=DateRange(op=">=", value="2020-01-01"),
            age=NumericRange(op=">", value=1)
        )
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) >= 2
        assert any("C.start_date" in clause for clause in where_clauses)
        assert any("P.year_of_birth" in clause for clause in where_clauses)


class TestLocationRegionSqlBuilder:
    """Test LocationRegionSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = LocationRegionSqlBuilder()
        template = builder.get_query_template()
        
        assert "@selectClause" in template
        assert "@codesetClause" in template
        assert "@joinClause" in template
        assert "@whereClause" in template
        assert "@ordinalExpression" in template
        assert "@additionalColumns" in template
        assert "LOCATION" in template
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = LocationRegionSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        assert default_cols == expected_cols
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = LocationRegionSqlBuilder()
        
        assert builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT) == "C.region_concept_id"
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = LocationRegionSqlBuilder()
        criteria = LocationRegion()
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        assert "@codesetClause" not in result
        assert result == "SELECT * FROM table "
    
    def test_embed_ordinal_expression(self):
        """Test ordinal expression embedding."""
        builder = LocationRegionSqlBuilder()
        criteria = LocationRegion()
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert len(where_clauses) == 0
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = LocationRegionSqlBuilder()
        criteria = LocationRegion()
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        assert len(join_clauses) == 0
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = LocationRegionSqlBuilder()
        criteria = LocationRegion()
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        assert len(where_clauses) == 0


class TestBuilderIntegration:
    """Integration tests for all builders."""
    
    def test_all_builders_have_required_methods(self):
        """Test that all builders implement required methods."""
        builders = [
            DoseEraSqlBuilder(),
            ObservationPeriodSqlBuilder(),
            PayerPlanPeriodSqlBuilder(),
            VisitDetailSqlBuilder(),
            LocationRegionSqlBuilder()
        ]
        
        for builder in builders:
            # Test required abstract methods
            assert hasattr(builder, 'get_query_template')
            assert hasattr(builder, 'get_default_columns')
            assert hasattr(builder, 'get_table_column_for_criteria_column')
            assert hasattr(builder, 'embed_codeset_clause')
            assert hasattr(builder, 'embed_ordinal_expression')
            assert hasattr(builder, 'resolve_select_clauses')
            assert hasattr(builder, 'resolve_join_clauses')
            assert hasattr(builder, 'resolve_where_clauses')
            
            # Test that methods are callable
            assert callable(builder.get_query_template)
            assert callable(builder.get_default_columns)
            assert callable(builder.get_table_column_for_criteria_column)
    
    def test_builder_options_integration(self):
        """Test builders work with BuilderOptions."""
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        builders = [
            DoseEraSqlBuilder(),
            ObservationPeriodSqlBuilder(),
            PayerPlanPeriodSqlBuilder(),
            VisitDetailSqlBuilder(),
            LocationRegionSqlBuilder()
        ]
        
        for builder in builders:
            # Test that builders can handle options
            assert isinstance(builder.get_default_columns(), set)
            # Create mock criteria with required fields
            if builder.__class__.__name__ == "DoseEraSqlBuilder":
                mock_criteria = DoseEra(first=False)
            elif builder.__class__.__name__ == "VisitDetailSqlBuilder":
                mock_criteria = VisitDetail(visit_detail_type_exclude=False)
            else:
                mock_criteria = Mock()
            
            assert isinstance(builder.resolve_select_clauses(mock_criteria, options), list)
            assert isinstance(builder.resolve_join_clauses(mock_criteria, options), list)
            assert isinstance(builder.resolve_where_clauses(mock_criteria, options), list)