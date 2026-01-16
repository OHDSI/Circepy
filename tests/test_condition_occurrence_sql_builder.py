"""
Comprehensive tests for ConditionOccurrenceSqlBuilder.

This module tests the ConditionOccurrenceSqlBuilder implementation
with comprehensive coverage of all methods and edge cases.
"""

import unittest
from unittest.mock import Mock, patch
from typing import List, Set, Optional

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from circe.cohortdefinition.builders import (
    BuilderUtils, BuilderOptions, CriteriaColumn,
    ConditionOccurrenceSqlBuilder
)
from circe.cohortdefinition.criteria import ConditionOccurrence
from circe.vocabulary.concept import Concept
from circe.cohortdefinition.core import (
    DateRange, DateAdjustment, NumericRange, TextFilter,
    ConceptSetSelection, DateType
)


class TestConditionOccurrenceSqlBuilder(unittest.TestCase):
    """Comprehensive test suite for ConditionOccurrenceSqlBuilder."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.builder = ConditionOccurrenceSqlBuilder()
        self.criteria = ConditionOccurrence()
    
    def test_get_default_columns(self):
        """Test get_default_columns method."""
        result = self.builder.get_default_columns()
        expected = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID
        }
        self.assertEqual(result, expected)
    
    def test_get_query_template(self):
        """Test get_query_template method."""
        result = self.builder.get_query_template()
        self.assertIn("-- Begin Condition Occurrence Criteria", result)
        self.assertIn("-- End Condition Occurrence Criteria", result)
        self.assertIn("@selectClause", result)
        self.assertIn("@ordinalExpression", result)
        self.assertIn("@codesetClause", result)
        self.assertIn("@joinClause", result)
        self.assertIn("@whereClause", result)
        self.assertIn("@additionalColumns", result)
    
    def test_get_table_column_for_criteria_column_domain_concept(self):
        """Test table column mapping for domain concept."""
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT)
        self.assertEqual(result, "C.condition_concept_id")
    
    def test_get_table_column_for_criteria_column_duration(self):
        """Test table column mapping for duration."""
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION)
        self.assertEqual(result, "(DATEDIFF(d,C.start_date, C.end_date))")
    
    def test_get_table_column_for_criteria_column_start_date(self):
        """Test table column mapping for start date."""
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE)
        self.assertEqual(result, "C.start_date")
    
    def test_get_table_column_for_criteria_column_end_date(self):
        """Test table column mapping for end date."""
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE)
        self.assertEqual(result, "C.end_date")
    
    def test_get_table_column_for_criteria_column_visit_id(self):
        """Test table column mapping for visit ID."""
        result = self.builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID)
        self.assertEqual(result, "C.visit_occurrence_id")
    

    
    def test_embed_codeset_clause_with_codeset_id(self):
        """Test codeset clause embedding with codeset_id."""
        criteria = ConditionOccurrence(codeset_id=123)
        query = "SELECT * FROM table @codesetClause WHERE condition"
        result = self.builder.embed_codeset_clause(query, criteria)
        # Should contain codeset join expression
        self.assertNotEqual(result, query)
        self.assertNotIn("@codesetClause", result)
    
    def test_embed_codeset_clause_with_condition_source_concept(self):
        """Test codeset clause embedding with condition_source_concept."""
        criteria = ConditionOccurrence(condition_source_concept=456)
        query = "SELECT * FROM table @codesetClause WHERE condition"
        result = self.builder.embed_codeset_clause(query, criteria)
        # Should contain codeset join expression
        self.assertNotEqual(result, query)
        self.assertNotIn("@codesetClause", result)
    
    def test_embed_codeset_clause_without_codeset(self):
        """Test codeset clause embedding without codeset."""
        query = "SELECT * FROM table @codesetClause WHERE condition"
        result = self.builder.embed_codeset_clause(query, self.criteria)
        expected = "SELECT * FROM table  WHERE condition"
        self.assertEqual(result, expected)
    
    def test_embed_ordinal_expression_with_first_true(self):
        """Test ordinal expression embedding with first=True."""
        criteria = ConditionOccurrence(first=True)
        query = "SELECT @ordinalExpression FROM table"
        where_clauses = []
        result = self.builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertIn("row_number() over (PARTITION BY co.person_id ORDER BY co.condition_start_date, co.condition_occurrence_id) as ordinal", result)
        self.assertIn("C.ordinal = 1", where_clauses)
        self.assertNotIn("@ordinalExpression", result)
    
    def test_embed_ordinal_expression_with_first_false(self):
        """Test ordinal expression embedding with first=False."""
        criteria = ConditionOccurrence(first=False)
        query = "SELECT @ordinalExpression FROM table"
        where_clauses = []
        result = self.builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertNotIn("row_number()", result)
        self.assertNotIn("C.ordinal = 1", where_clauses)
        self.assertNotIn("@ordinalExpression", result)
    
    def test_embed_ordinal_expression_with_first_none(self):
        """Test ordinal expression embedding with first=None."""
        criteria = ConditionOccurrence(first=None)
        query = "SELECT @ordinalExpression FROM table"
        where_clauses = []
        result = self.builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertNotIn("row_number()", result)
        self.assertNotIn("C.ordinal = 1", where_clauses)
        self.assertNotIn("@ordinalExpression", result)
    
    def test_resolve_select_clauses_basic(self):
        """Test basic select clauses resolution."""
        result = self.builder.resolve_select_clauses(self.criteria)
        expected = [
            "co.person_id",
            "co.condition_occurrence_id",
            "co.condition_concept_id",
            "co.visit_occurrence_id",
            "co.condition_start_date as start_date, COALESCE(co.condition_end_date, DATEADD(day,1,co.condition_start_date)) as end_date"
        ]
        self.assertEqual(result, expected)
    
    def test_resolve_select_clauses_with_condition_type(self):
        """Test select clauses with condition_type."""
        criteria = ConditionOccurrence(condition_type=[Concept(concept_id=1)])
        result = self.builder.resolve_select_clauses(criteria)
        self.assertIn("co.condition_type_concept_id", result)
    
    def test_resolve_select_clauses_with_condition_type_cs(self):
        """Test select clauses with condition_type_cs."""
        criteria = ConditionOccurrence(condition_type_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_select_clauses(criteria)
        self.assertIn("co.condition_type_concept_id", result)
    
    def test_resolve_select_clauses_with_stop_reason(self):
        """Test select clauses with stop_reason."""
        criteria = ConditionOccurrence(stop_reason=TextFilter(text="test"))
        result = self.builder.resolve_select_clauses(criteria)
        self.assertIn("co.stop_reason", result)
    
    def test_resolve_select_clauses_with_provider_specialty(self):
        """Test select clauses with provider_specialty."""
        criteria = ConditionOccurrence(provider_specialty=[Concept(concept_id=1)])
        result = self.builder.resolve_select_clauses(criteria)
        self.assertIn("co.provider_id", result)
    
    def test_resolve_select_clauses_with_provider_specialty_cs(self):
        """Test select clauses with provider_specialty_cs."""
        criteria = ConditionOccurrence(provider_specialty_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_select_clauses(criteria)
        self.assertIn("co.provider_id", result)
    
    def test_resolve_select_clauses_with_condition_status(self):
        """Test select clauses with condition_status."""
        criteria = ConditionOccurrence(condition_status=[Concept(concept_id=1)])
        result = self.builder.resolve_select_clauses(criteria)
        self.assertIn("co.condition_status_concept_id", result)
    
    def test_resolve_select_clauses_with_condition_status_cs(self):
        """Test select clauses with condition_status_cs."""
        criteria = ConditionOccurrence(condition_status_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_select_clauses(criteria)
        self.assertIn("co.condition_status_concept_id", result)
    
    def test_resolve_select_clauses_with_date_adjustment(self):
        """Test select clauses with date_adjustment."""
        criteria = ConditionOccurrence(date_adjustment=DateAdjustment(
            start_offset=30,
            end_offset=0,
            start_with="start_date",
            end_with="start_date"
        ))
        result = self.builder.resolve_select_clauses(criteria)
        # Should contain DATEADD expression
        self.assertTrue(any("DATEADD" in item for item in result))
    
    def test_resolve_join_clauses_basic(self):
        """Test basic join clauses resolution."""
        result = self.builder.resolve_join_clauses(self.criteria)
        self.assertEqual(result, [])
    
    def test_resolve_join_clauses_with_age(self):
        """Test join clauses with age criteria."""
        criteria = ConditionOccurrence(age=NumericRange(op="gte", value=18, extent=65))
        result = self.builder.resolve_join_clauses(criteria)
        self.assertIn("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id", result)
    
    def test_resolve_join_clauses_with_gender(self):
        """Test join clauses with gender criteria."""
        criteria = ConditionOccurrence(gender=[Concept(concept_id=1)])
        result = self.builder.resolve_join_clauses(criteria)
        self.assertIn("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id", result)
    
    def test_resolve_join_clauses_with_gender_cs(self):
        """Test join clauses with gender_cs criteria."""
        criteria = ConditionOccurrence(gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_join_clauses(criteria)
        self.assertIn("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id", result)
    
    def test_resolve_join_clauses_with_visit_type(self):
        """Test join clauses with visit_type criteria."""
        criteria = ConditionOccurrence(visit_type=[Concept(concept_id=1)])
        result = self.builder.resolve_join_clauses(criteria)
        self.assertIn("JOIN @cdm_database_schema.VISIT_OCCURRENCE V on C.visit_occurrence_id = V.visit_occurrence_id and C.person_id = V.person_id", result)
    
    def test_resolve_join_clauses_with_visit_type_cs(self):
        """Test join clauses with visit_type_cs criteria."""
        criteria = ConditionOccurrence(visit_type_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_join_clauses(criteria)
        self.assertIn("JOIN @cdm_database_schema.VISIT_OCCURRENCE V on C.visit_occurrence_id = V.visit_occurrence_id and C.person_id = V.person_id", result)
    
    def test_resolve_join_clauses_with_provider_specialty(self):
        """Test join clauses with provider_specialty criteria."""
        criteria = ConditionOccurrence(provider_specialty=[Concept(concept_id=1)])
        result = self.builder.resolve_join_clauses(criteria)
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id", result)
    
    def test_resolve_join_clauses_with_provider_specialty_cs(self):
        """Test join clauses with provider_specialty_cs criteria."""
        criteria = ConditionOccurrence(provider_specialty_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_join_clauses(criteria)
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id", result)
    
    def test_resolve_join_clauses_with_multiple_conditions(self):
        """Test join clauses with multiple conditions."""
        criteria = ConditionOccurrence(
            age=NumericRange(op="gte", value=18, extent=65),
            visit_type=[Concept(concept_id=1)],
            provider_specialty=[Concept(concept_id=1)]
        )
        result = self.builder.resolve_join_clauses(criteria)
        self.assertEqual(len(result), 3)
        self.assertIn("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id", result)
        self.assertIn("JOIN @cdm_database_schema.VISIT_OCCURRENCE V on C.visit_occurrence_id = V.visit_occurrence_id and C.person_id = V.person_id", result)
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id", result)
    
    def test_resolve_where_clauses_basic(self):
        """Test basic where clauses resolution."""
        result = self.builder.resolve_where_clauses(self.criteria)
        self.assertEqual(result, [])
    
    def test_resolve_where_clauses_with_occurrence_start_date(self):
        """Test where clauses with occurrence_start_date."""
        criteria = ConditionOccurrence(occurrence_start_date=DateRange(op="gte", value="2020-01-01", extent="2020-12-31"))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("C.start_date" in clause for clause in result))
    
    def test_resolve_where_clauses_with_occurrence_end_date(self):
        """Test where clauses with occurrence_end_date."""
        criteria = ConditionOccurrence(occurrence_end_date=DateRange(op="gte", value="2020-01-01", extent="2020-12-31"))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("C.end_date" in clause for clause in result))
    
    def test_resolve_where_clauses_with_condition_type(self):
        """Test where clauses with condition_type."""
        criteria = ConditionOccurrence(condition_type=[Concept(concept_id=1)])
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("C.condition_type_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_condition_type_exclude(self):
        """Test where clauses with condition_type_exclude=True."""
        criteria = ConditionOccurrence(
            condition_type=[Concept(concept_id=1)],
            condition_type_exclude=True
        )
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("not" in clause for clause in result))
    
    def test_resolve_where_clauses_with_condition_type_cs(self):
        """Test where clauses with condition_type_cs."""
        criteria = ConditionOccurrence(condition_type_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("C.condition_type_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_stop_reason(self):
        """Test where clauses with stop_reason."""
        criteria = ConditionOccurrence(stop_reason=TextFilter(text="test"))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("C.stop_reason" in clause for clause in result))
    
    def test_resolve_where_clauses_with_age(self):
        """Test where clauses with age criteria."""
        criteria = ConditionOccurrence(age=NumericRange(op="gte", value=18, extent=65))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("YEAR(C.start_date) - P.year_of_birth" in clause for clause in result))
    
    def test_resolve_where_clauses_with_gender(self):
        """Test where clauses with gender criteria."""
        criteria = ConditionOccurrence(gender=[Concept(concept_id=1)])
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("P.gender_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_gender_cs(self):
        """Test where clauses with gender_cs criteria."""
        criteria = ConditionOccurrence(gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("P.gender_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_provider_specialty(self):
        """Test where clauses with provider_specialty criteria."""
        criteria = ConditionOccurrence(provider_specialty=[Concept(concept_id=1)])
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("PR.specialty_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_provider_specialty_cs(self):
        """Test where clauses with provider_specialty_cs criteria."""
        criteria = ConditionOccurrence(provider_specialty_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("PR.specialty_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_visit_type(self):
        """Test where clauses with visit_type criteria."""
        criteria = ConditionOccurrence(visit_type=[Concept(concept_id=1)])
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("V.visit_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_visit_type_cs(self):
        """Test where clauses with visit_type_cs criteria."""
        criteria = ConditionOccurrence(visit_type_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("V.visit_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_condition_status(self):
        """Test where clauses with condition_status criteria."""
        criteria = ConditionOccurrence(condition_status=[Concept(concept_id=1)])
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("C.condition_status_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_condition_status_cs(self):
        """Test where clauses with condition_status_cs criteria."""
        criteria = ConditionOccurrence(condition_status_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False))
        result = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("C.condition_status_concept_id" in clause for clause in result))
    
    def test_resolve_where_clauses_with_multiple_conditions(self):
        """Test where clauses with multiple conditions."""
        criteria = ConditionOccurrence(
            occurrence_start_date=DateRange(op="gte", value="2020-01-01", extent="2020-12-31"),
            age=NumericRange(op="gte", value=18, extent=65),
            gender=[Concept(concept_id=1)]
        )
        result = self.builder.resolve_where_clauses(criteria)
        self.assertGreater(len(result), 0)
        self.assertTrue(any("C.start_date" in clause for clause in result))
        self.assertTrue(any("YEAR(C.start_date) - P.year_of_birth" in clause for clause in result))
        self.assertTrue(any("P.gender_concept_id" in clause for clause in result))
    
    def test_get_criteria_sql_basic(self):
        """Test basic SQL generation."""
        result = self.builder.get_criteria_sql(self.criteria)
        
        # Check that template placeholders are replaced
        self.assertNotIn("@selectClause", result)
        self.assertNotIn("@ordinalExpression", result)
        self.assertNotIn("@codesetClause", result)
        self.assertNotIn("@joinClause", result)
        self.assertNotIn("@whereClause", result)
        self.assertNotIn("@additionalColumns", result)
        
        # Check that SQL structure is maintained
        self.assertIn("-- Begin Condition Occurrence Criteria", result)
        self.assertIn("-- End Condition Occurrence Criteria", result)
        self.assertIn("SELECT C.person_id", result)
        self.assertIn("FROM", result)
    
    def test_get_criteria_sql_with_codeset_id(self):
        """Test SQL generation with codeset_id."""
        criteria = ConditionOccurrence(codeset_id=123)
        result = self.builder.get_criteria_sql(criteria)
        
        # Should not contain template placeholders
        self.assertNotIn("@codesetClause", result)
        self.assertNotIn("@selectClause", result)
        self.assertNotIn("@ordinalExpression", result)
        self.assertNotIn("@joinClause", result)
        self.assertNotIn("@whereClause", result)
        self.assertNotIn("@additionalColumns", result)
    
    def test_get_criteria_sql_with_first_true(self):
        """Test SQL generation with first=True."""
        criteria = ConditionOccurrence(first=True)
        result = self.builder.get_criteria_sql(criteria)
        
        # Should contain ordinal expression
        self.assertIn("row_number()", result)
        self.assertIn("C.ordinal = 1", result)
    
    def test_get_criteria_sql_with_date_adjustment(self):
        """Test SQL generation with date_adjustment."""
        criteria = ConditionOccurrence(date_adjustment=DateAdjustment(
            start_offset=30,
            end_offset=0,
            start_with="start_date",
            end_with="start_date"
        ))
        result = self.builder.get_criteria_sql(criteria)
        
        # Should contain DATEADD expression
        self.assertIn("DATEADD", result)
    
    def test_get_criteria_sql_with_person_join(self):
        """Test SQL generation with person join."""
        criteria = ConditionOccurrence(age=NumericRange(op="gte", value=18, extent=65))
        result = self.builder.get_criteria_sql(criteria)
        
        # Should contain person join
        self.assertIn("JOIN @cdm_database_schema.PERSON P", result)
    
    def test_get_criteria_sql_with_options(self):
        """Test SQL generation with builder options."""
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.DOMAIN_CONCEPT]
        
        result = self.builder.get_criteria_sql_with_options(self.criteria, options)
        
        # Check that additional columns are included as NULL
        self.assertIn("C.condition_concept_id as domain_concept_id", result)
    
    def test_get_criteria_sql_with_options_none(self):
        """Test SQL generation with None options."""
        result = self.builder.get_criteria_sql_with_options(self.criteria, None)
        
        # Should work without errors
        self.assertIsInstance(result, str)
        self.assertIn("-- Begin Condition Occurrence Criteria", result)
    
    def test_edge_case_empty_gender_list(self):
        """Test edge case with empty gender list."""
        criteria = ConditionOccurrence(gender=[])
        result = self.builder.resolve_where_clauses(criteria)
        # Should not add gender clause for empty list
        self.assertFalse(any("P.gender_concept_id" in clause for clause in result))
    
    def test_edge_case_gender_with_none_concept_id(self):
        """Test edge case with gender containing None concept_id."""
        # This tests Java interoperability - Java can send null concept_id values
        criteria = ConditionOccurrence(gender=[Concept(concept_id=None)])
        result = self.builder.resolve_where_clauses(criteria)
        # Should handle None concept_id gracefully by filtering it out
        self.assertIsInstance(result, list)
        # Should not add gender clause since all concept_ids are None
        self.assertFalse(any("P.gender_concept_id" in clause for clause in result))
    
    def test_edge_case_date_range_none_values(self):
        """Test edge case with date range containing None values."""
        criteria = ConditionOccurrence(occurrence_start_date=DateRange(op="gte", value=None, extent=None))
        result = self.builder.resolve_where_clauses(criteria)
        # Should handle None values gracefully
        self.assertIsInstance(result, list)
    
    def test_edge_case_numeric_range_none_values(self):
        """Test edge case with numeric range containing None values."""
        criteria = ConditionOccurrence(age=NumericRange(op="gte", value=None, extent=None))
        result = self.builder.resolve_where_clauses(criteria)
        # Should handle None values gracefully
        self.assertIsInstance(result, list)
    
    def test_comprehensive_integration_test(self):
        """Test comprehensive integration with multiple criteria."""
        criteria = ConditionOccurrence(
            codeset_id=123,
            first=True,
            occurrence_start_date=DateRange(op="gte", value="2020-01-01", extent="2020-12-31"),
            occurrence_end_date=DateRange(op="gte", value="2020-01-01", extent="2020-12-31"),
            condition_type=[Concept(concept_id=1)],
            condition_type_exclude=False,
            stop_reason=TextFilter(text="test"),
            age=NumericRange(op="gte", value=18, extent=65),
            gender=[Concept(concept_id=1)],
            visit_type=[Concept(concept_id=1)],
            provider_specialty=[Concept(concept_id=1)],
            condition_status=[Concept(concept_id=1)],
            date_adjustment=DateAdjustment(
                start_offset=30,
                end_offset=0,
                start_with="start_date",
                end_with="start_date"
            )
        )
        
        result = self.builder.get_criteria_sql(criteria)
        
        # Should generate complete SQL without template placeholders (except @cdm_database_schema which is expected)
        self.assertNotIn("@selectClause", result)
        self.assertNotIn("@ordinalExpression", result)
        self.assertNotIn("@codesetClause", result)
        self.assertNotIn("@joinClause", result)
        self.assertNotIn("@whereClause", result)
        self.assertNotIn("@additionalColumns", result)
        self.assertIn("-- Begin Condition Occurrence Criteria", result)
        self.assertIn("-- End Condition Occurrence Criteria", result)
        self.assertIn("SELECT C.person_id", result)
        self.assertIn("FROM", result)
        
        # Should contain various clauses
        self.assertIn("row_number()", result)  # ordinal expression
        self.assertIn("JOIN @cdm_database_schema.PERSON P", result)  # person join
        self.assertIn("JOIN @cdm_database_schema.VISIT_OCCURRENCE V", result)  # visit join
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR", result)  # provider join


if __name__ == '__main__':
    unittest.main()
