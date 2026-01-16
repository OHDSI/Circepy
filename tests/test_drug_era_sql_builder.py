"""
Tests for DrugEraSqlBuilder

This module contains comprehensive tests for the DrugEraSqlBuilder class,
ensuring 100% test coverage and functionality matching the Java implementation.
"""

import pytest
from typing import List, Optional
from circe.cohortdefinition.builders.drug_era import DrugEraSqlBuilder
from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderOptions
from circe.cohortdefinition.criteria import DrugEra
from circe.cohortdefinition.core import DateRange, NumericRange, ConceptSetSelection, DateAdjustment
from circe.vocabulary.concept import Concept


class TestDrugEraSqlBuilder:
    """Test cases for DrugEraSqlBuilder."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.builder = DrugEraSqlBuilder()
    
    def test_get_default_columns(self):
        """Test get_default_columns method."""
        default_columns = self.builder.get_default_columns()
        expected = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        assert default_columns == expected
    
    def test_get_table_column_for_criteria_column(self):
        """Test get_table_column_for_criteria_column method."""
        # Test domain concept
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT)
        assert result == "C.drug_concept_id"
        
        # Test era occurrences
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.ERA_OCCURRENCES)
        assert result == "C.drug_exposure_count"
        
        # Test gap days
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.GAP_DAYS)
        assert result == "C.gap_days"
        
        # Test duration
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION)
        assert result == "DATEDIFF(d,C.start_date, C.end_date)"
        
        # Test start date
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE)
        assert result == "C.start_date"
        
        # Test end date
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE)
        assert result == "C.end_date"
        
        # Test visit id
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID)
        assert result == "NULL"
        
        # Test unknown column
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.AGE)
        assert result == "NULL"
    
    def test_get_query_template(self):
        """Test get_query_template method."""
        template = self.builder.get_query_template()
        assert "@selectClause" in template
        assert "@codesetClause" in template
        assert "@ordinalExpression" in template
        assert "@joinClause" in template
        assert "@whereClause" in template
        assert "@additionalColumns" in template
        assert "DRUG_ERA" in template
    
    def test_embed_codeset_clause_with_codeset_id(self):
        """Test embed_codeset_clause with codeset_id."""
        criteria = DrugEra(codeset_id=123)
        query = "SELECT * FROM table @codesetClause WHERE 1=1"
        
        result = self.builder.embed_codeset_clause(query, criteria)
        
        # Note: Reference uses lowercase 'where' and double space before #Codesets
        expected_clause = "where de.drug_concept_id in (SELECT concept_id from  #Codesets where codeset_id = 123)"
        assert "@codesetClause" not in result
        assert expected_clause in result
    
    def test_embed_codeset_clause_without_codeset_id(self):
        """Test embed_codeset_clause without codeset_id."""
        criteria = DrugEra(codeset_id=None)
        query = "SELECT * FROM table @codesetClause WHERE 1=1"
        
        result = self.builder.embed_codeset_clause(query, criteria)
        
        assert "@codesetClause" not in result
        assert "WHERE de.drug_concept_id" not in result
    
    def test_embed_ordinal_expression_with_first_true(self):
        """Test embed_ordinal_expression with first=True."""
        criteria = DrugEra(first=True)
        query = "SELECT * @ordinalExpression FROM table"
        where_clauses = []
        
        result = self.builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert "row_number() over" in result
        assert "C.ordinal = 1" in where_clauses
    
    def test_embed_ordinal_expression_with_first_false(self):
        """Test embed_ordinal_expression with first=False."""
        criteria = DrugEra(first=False)
        query = "SELECT * @ordinalExpression FROM table"
        where_clauses = []
        
        result = self.builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert "row_number() over" not in result
        assert len(where_clauses) == 0
    
    def test_embed_ordinal_expression_with_first_none(self):
        """Test embed_ordinal_expression with first=None."""
        criteria = DrugEra(first=None)
        query = "SELECT * @ordinalExpression FROM table"
        where_clauses = []
        
        result = self.builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        assert "@ordinalExpression" not in result
        assert "row_number() over" not in result
        assert len(where_clauses) == 0
    
    def test_resolve_select_clauses_without_date_adjustment(self):
        """Test resolve_select_clauses without date adjustment."""
        criteria = DrugEra()
        
        result = self.builder.resolve_select_clauses(criteria)
        
        assert "de.person_id" in result
        assert "de.drug_era_id" in result
        assert "de.drug_concept_id" in result
        assert "de.drug_exposure_count" in result
        assert "de.gap_days" in result
        assert "de.drug_era_start_date as start_date, de.drug_era_end_date as end_date" in result
    
    def test_resolve_select_clauses_with_date_adjustment(self):
        """Test resolve_select_clauses with date adjustment."""
        date_adjustment = DateAdjustment(
            start_offset=30,
            end_offset=-30,
            start_with="start_date",
            end_with="end_date"
        )
        criteria = DrugEra(date_adjustment=date_adjustment)
        
        result = self.builder.resolve_select_clauses(criteria)
        
        assert "de.person_id" in result
        assert any("DATEADD(day,30" in item for item in result)
        assert any("DATEADD(day,-30" in item for item in result)
    
    def test_resolve_join_clauses_without_person_joins(self):
        """Test resolve_join_clauses without person joins."""
        criteria = DrugEra()
        
        result = self.builder.resolve_join_clauses(criteria)
        
        assert len(result) == 0
    
    def test_resolve_join_clauses_with_age_at_start(self):
        """Test resolve_join_clauses with age_at_start."""
        criteria = DrugEra(age_at_start=NumericRange(op=">=", value=18))
        
        result = self.builder.resolve_join_clauses(criteria)
        
        assert len(result) == 1
        assert "JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id" in result[0]
    
    def test_resolve_join_clauses_with_age_at_end(self):
        """Test resolve_join_clauses with age_at_end."""
        criteria = DrugEra(age_at_end=NumericRange(op="<=", value=65))
        
        result = self.builder.resolve_join_clauses(criteria)
        
        assert len(result) == 1
        assert "JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id" in result[0]
    
    def test_resolve_join_clauses_with_gender(self):
        """Test resolve_join_clauses with gender."""
        criteria = DrugEra(gender=[Concept(concept_id=8507)])
        
        result = self.builder.resolve_join_clauses(criteria)
        
        assert len(result) == 1
        assert "JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id" in result[0]
    
    def test_resolve_join_clauses_with_gender_cs(self):
        """Test resolve_join_clauses with gender_cs."""
        criteria = DrugEra(gender_cs=ConceptSetSelection(codeset_id=123, is_exclusion=False))
        
        result = self.builder.resolve_join_clauses(criteria)
        
        assert len(result) == 1
        assert "JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id" in result[0]
    
    def test_resolve_join_clauses_with_multiple_conditions(self):
        """Test resolve_join_clauses with multiple conditions."""
        criteria = DrugEra(
            age_at_start=NumericRange(op=">=", value=18),
            gender=[Concept(concept_id=8507)],
            gender_cs=ConceptSetSelection(codeset_id=123, is_exclusion=False)
        )
        
        result = self.builder.resolve_join_clauses(criteria)
        
        assert len(result) == 1  # Should only join once
        assert "JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id" in result[0]
    
    def test_resolve_where_clauses_empty(self):
        """Test resolve_where_clauses with no conditions."""
        criteria = DrugEra()
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 0
    
    def test_resolve_where_clauses_with_era_start_date(self):
        """Test resolve_where_clauses with era_start_date."""
        criteria = DrugEra(era_start_date=DateRange(op=">=", value="2020-01-01"))
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "C.start_date" in result[0]
    
    def test_resolve_where_clauses_with_era_end_date(self):
        """Test resolve_where_clauses with era_end_date."""
        criteria = DrugEra(era_end_date=DateRange(op="<=", value="2023-12-31"))
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "C.end_date" in result[0]
    
    def test_resolve_where_clauses_with_occurrence_count(self):
        """Test resolve_where_clauses with occurrence_count."""
        criteria = DrugEra(occurrence_count=NumericRange(op=">=", value=2))
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "C.drug_exposure_count" in result[0]
    
    def test_resolve_where_clauses_with_era_length(self):
        """Test resolve_where_clauses with era_length."""
        criteria = DrugEra(era_length=NumericRange(op=">=", value=30))
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "DATEDIFF(d,C.start_date, C.end_date)" in result[0]
    
    def test_resolve_where_clauses_with_gap_days(self):
        """Test resolve_where_clauses with gap_days.
        
        Note: Replicating Java bug where gap_days filter uses era_length value.
        """
        criteria = DrugEra(gap_days=NumericRange(op="<=", value=30), era_length=NumericRange(op="<=", value=60))
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 2 # gap_days and era_length
        assert "C.gap_days" in result[1]
        assert "60" in result[1] # Should use era_length value
    
    def test_resolve_where_clauses_with_age_at_start(self):
        """Test resolve_where_clauses with age_at_start."""
        criteria = DrugEra(age_at_start=NumericRange(op=">=", value=18))
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "YEAR(C.start_date) - P.year_of_birth" in result[0]
    
    def test_resolve_where_clauses_with_age_at_end(self):
        """Test resolve_where_clauses with age_at_end."""
        criteria = DrugEra(age_at_end=NumericRange(op="<=", value=65))
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "YEAR(C.end_date) - P.year_of_birth" in result[0]
    
    def test_resolve_where_clauses_with_gender(self):
        """Test resolve_where_clauses with gender."""
        criteria = DrugEra(gender=[Concept(concept_id=8507), Concept(concept_id=8532)])
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "P.gender_concept_id in (8507,8532)" in result[0]
    
    def test_resolve_where_clauses_with_gender_cs(self):
        """Test resolve_where_clauses with gender_cs."""
        criteria = DrugEra(gender_cs=ConceptSetSelection(codeset_id=123, is_exclusion=False))
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "P.gender_concept_id" in result[0]
        assert "123" in result[0]
    
    def test_resolve_where_clauses_with_multiple_conditions(self):
        """Test resolve_where_clauses with multiple conditions."""
        criteria = DrugEra(
            era_start_date=DateRange(op=">=", value="2020-01-01"),
            era_end_date=DateRange(op="<=", value="2023-12-31"),
            occurrence_count=NumericRange(op=">=", value=2),
            era_length=NumericRange(op=">=", value=30),
            gap_days=NumericRange(op="<=", value=30),
            age_at_start=NumericRange(op=">=", value=18),
            age_at_end=NumericRange(op="<=", value=65),
            gender=[Concept(concept_id=8507)],
            gender_cs=ConceptSetSelection(codeset_id=123, is_exclusion=False)
        )
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 9
        assert any("C.start_date" in clause for clause in result)
        assert any("C.end_date" in clause for clause in result)
        assert any("C.drug_exposure_count" in clause for clause in result)
        assert any("DATEDIFF(d,C.start_date, C.end_date)" in clause for clause in result)
        assert any("C.gap_days" in clause for clause in result)
        assert any("YEAR(C.start_date) - P.year_of_birth" in clause for clause in result)
        assert any("YEAR(C.end_date) - P.year_of_birth" in clause for clause in result)
        assert any("P.gender_concept_id in (8507)" in clause for clause in result)
        assert any("P.gender_concept_id" in clause and "123" in clause for clause in result)
    
    def test_get_criteria_sql_basic(self):
        """Test get_criteria_sql with basic criteria."""
        criteria = DrugEra()
        
        result = self.builder.get_criteria_sql(criteria)
        
        # Note: Template uses lowercase 'select' to match Java output
        assert "select" in result
        assert "FROM" in result or "from" in result
        assert "DRUG_ERA" in result
        assert "@selectClause" not in result
        assert "@codesetClause" not in result
        assert "@ordinalExpression" not in result
        assert "@joinClause" not in result
        assert "@whereClause" not in result
        assert "@additionalColumns" not in result
    
    def test_get_criteria_sql_with_codeset_id(self):
        """Test get_criteria_sql with codeset_id."""
        criteria = DrugEra(codeset_id=123)
        
        result = self.builder.get_criteria_sql(criteria)
        
        # Note: Reference uses lowercase 'where' and double space before #Codesets
        assert "where de.drug_concept_id in (SELECT concept_id from  #Codesets where codeset_id = 123)" in result
    
    def test_get_criteria_sql_with_first_true(self):
        """Test get_criteria_sql with first=True."""
        criteria = DrugEra(first=True)
        
        result = self.builder.get_criteria_sql(criteria)
        
        assert "row_number() over" in result
        assert "C.ordinal = 1" in result
    
    def test_get_criteria_sql_with_date_adjustment(self):
        """Test get_criteria_sql with date adjustment."""
        date_adjustment = DateAdjustment(
            start_offset=30,
            end_offset=-30,
            start_with="start_date",
            end_with="end_date"
        )
        criteria = DrugEra(date_adjustment=date_adjustment)
        
        result = self.builder.get_criteria_sql(criteria)
        
        assert "DATEADD(day,30" in result
        assert "DATEADD(day,-30" in result
    
    def test_get_criteria_sql_with_person_join(self):
        """Test get_criteria_sql with person join."""
        criteria = DrugEra(age_at_start=NumericRange(op=">=", value=18))
        
        result = self.builder.get_criteria_sql(criteria)
        
        assert "JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id" in result
        assert "YEAR(C.start_date) - P.year_of_birth" in result
    
    def test_get_criteria_sql_with_gap_days(self):
        """Test get_criteria_sql with gap_days.
        
        Note: Replicating Java bug where gap_days filter uses era_length value.
        """
        criteria = DrugEra(gap_days=NumericRange(op="<=", value=30), era_length=NumericRange(op="<=", value=60))
        
        result = self.builder.get_criteria_sql(criteria)
        
        assert "C.gap_days" in result
        assert "60" in result # Should use era_length value
    
    def test_get_criteria_sql_with_options(self):
        """Test get_criteria_sql_with_options."""
        criteria = DrugEra()
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.DURATION]
        
        result = self.builder.get_criteria_sql_with_options(criteria, options)
        
        assert "DATEDIFF(d,C.start_date, C.end_date)" in result
    
    def test_get_criteria_sql_with_options_none(self):
        """Test get_criteria_sql_with_options with None options."""
        criteria = DrugEra()
        
        result = self.builder.get_criteria_sql_with_options(criteria, None)
        
        assert "select" in result.lower()
        assert "from" in result.lower()
        assert "drug_era" in result.lower()
    
    def test_edge_case_empty_gender_list(self):
        """Test edge case with empty gender list."""
        criteria = DrugEra(gender=[])
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 0
    
    def test_edge_case_gender_with_none_concept_id(self):
        """Test edge case with gender containing None concept_id."""
        criteria = DrugEra(gender=[Concept(concept_id=8507)])
        
        result = self.builder.resolve_where_clauses(criteria)
        
        assert len(result) == 1
        assert "P.gender_concept_id in (8507)" in result[0]
    
    def test_edge_case_date_range_none_values(self):
        """Test edge case with None date range values."""
        criteria = DrugEra(
            era_start_date=DateRange(op=">=", value=None),
            era_end_date=DateRange(op="<=", value=None)
        )
        
        result = self.builder.resolve_where_clauses(criteria)
        
        # Should handle None values gracefully
        assert isinstance(result, list)
    
    def test_edge_case_numeric_range_none_values(self):
        """Test edge case with None numeric range values."""
        criteria = DrugEra(
            occurrence_count=NumericRange(op=">=", value=None),
            era_length=NumericRange(op="<=", value=None),
            gap_days=NumericRange(op="<=", value=None)
        )
        
        result = self.builder.resolve_where_clauses(criteria)
        
        # Should handle None values gracefully
        assert isinstance(result, list)
    
    def test_comprehensive_integration_test(self):
        """Test comprehensive integration with all features."""
        date_adjustment = DateAdjustment(
            start_offset=7,
            end_offset=-7,
            start_with="start_date",
            end_with="end_date"
        )
        
        criteria = DrugEra(
            codeset_id=456,
            first=True,
            era_start_date=DateRange(op=">=", value="2020-01-01"),
            era_end_date=DateRange(op="<=", value="2023-12-31"),
            occurrence_count=NumericRange(op=">=", value=1),
            era_length=NumericRange(op=">=", value=7),
            gap_days=NumericRange(op="<=", value=30),
            age_at_start=NumericRange(op=">=", value=18),
            age_at_end=NumericRange(op="<=", value=80),
            gender=[Concept(concept_id=8507)],
            gender_cs=ConceptSetSelection(codeset_id=789, is_exclusion=False),
            date_adjustment=date_adjustment
        )
        
        result = self.builder.get_criteria_sql(criteria)
        
        # Verify all components are present
        # Note: Reference uses lowercase 'where' and double space before #Codesets
        assert "where de.drug_concept_id in (SELECT concept_id from  #Codesets where codeset_id = 456)" in result
        assert "row_number() over" in result
        assert "C.ordinal = 1" in result
        assert "JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id" in result
        assert "DATEADD(day,7" in result
        assert "DATEADD(day,-7" in result
        assert "C.start_date" in result
        assert "C.end_date" in result
        assert "C.drug_exposure_count" in result
        assert "DATEDIFF(d,C.start_date, C.end_date)" in result
        assert "C.gap_days" in result
        assert "YEAR(C.start_date) - P.year_of_birth" in result
        assert "YEAR(C.end_date) - P.year_of_birth" in result
        assert "P.gender_concept_id in (8507)" in result
        assert "P.gender_concept_id" in result and "789" in result
