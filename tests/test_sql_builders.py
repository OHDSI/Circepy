"""
Tests for New SQL Builders

This module contains comprehensive tests for all the new SQL builders
that were recently implemented.
"""

import unittest
import sys
import os
from typing import Set, List, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from circe.cohortdefinition.builders import (
    DeathSqlBuilder, VisitOccurrenceSqlBuilder, ObservationSqlBuilder,
    MeasurementSqlBuilder, DeviceExposureSqlBuilder, SpecimenSqlBuilder
)
from circe.cohortdefinition.builders.utils import BuilderOptions, CriteriaColumn
from circe.cohortdefinition.criteria import (
    Death, VisitOccurrence, Observation, Measurement, DeviceExposure, Specimen
)
from circe.cohortdefinition.core import DateRange, NumericRange, TextFilter, ConceptSetSelection
from circe.vocabulary.concept import Concept


class TestDeathSqlBuilder(unittest.TestCase):
    """Test DeathSqlBuilder class."""

    def test_death_sql_builder_initialization(self):
        """Test basic initialization of DeathSqlBuilder."""
        builder = DeathSqlBuilder()
        self.assertIsNotNone(builder)

    def test_get_query_template(self):
        """Test get_query_template method."""
        builder = DeathSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@cdm_database_schema.DEATH", template)

    def test_get_default_columns(self):
        """Test get_default_columns method."""
        builder = DeathSqlBuilder()
        columns = builder.get_default_columns()
        
        expected_columns = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT
        }
        self.assertEqual(columns, expected_columns)

    def test_get_table_column_for_criteria_column(self):
        """Test get_table_column_for_criteria_column method."""
        builder = DeathSqlBuilder()
        
        # Test each column type
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE),
            "C.death_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE),
            "C.death_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT),
            "C.death_type_concept_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION),
            "NULL"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID),
            "NULL"
        )

    def test_get_criteria_sql_basic(self):
        """Test get_criteria_sql with basic criteria."""
        builder = DeathSqlBuilder()
        criteria = Death(
            first=True,
            death_type_exclude=False
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.DEATH C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("ORDER BY C.death_date ASC", sql)

    def test_get_criteria_sql_with_options(self):
        """Test get_criteria_sql with builder options."""
        builder = DeathSqlBuilder()
        criteria = Death(
            first=True,
            death_type_exclude=False
        )
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.VISIT_ID]
        
        sql = builder.get_criteria_sql_with_options(criteria, options)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.DEATH C", sql)
        self.assertIn("WHERE", sql)

    def test_embed_codeset_clause(self):
        """Test embed_codeset_clause method."""
        builder = DeathSqlBuilder()
        criteria = Death(
            codeset_id=12345,
            first=True,
            death_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        self.assertIn("C.death_concept_id", clause)
        self.assertIn("12345", clause)

    def test_embed_codeset_clause_no_codeset(self):
        """Test embed_codeset_clause with no codeset ID."""
        builder = DeathSqlBuilder()
        criteria = Death(
            first=True,
            death_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        self.assertEqual(clause, "SELECT * FROM table ")


class TestVisitOccurrenceSqlBuilder(unittest.TestCase):
    """Test VisitOccurrenceSqlBuilder class."""

    def test_visit_occurrence_sql_builder_initialization(self):
        """Test basic initialization of VisitOccurrenceSqlBuilder."""
        builder = VisitOccurrenceSqlBuilder()
        self.assertIsNotNone(builder)

    def test_get_query_template(self):
        """Test get_query_template method."""
        builder = VisitOccurrenceSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@cdm_database_schema.VISIT_OCCURRENCE", template)

    def test_get_default_columns(self):
        """Test get_default_columns method."""
        builder = VisitOccurrenceSqlBuilder()
        columns = builder.get_default_columns()
        
        expected_columns = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.VISIT_ID
        }
        self.assertEqual(columns, expected_columns)

    def test_get_table_column_for_criteria_column(self):
        """Test get_table_column_for_criteria_column method."""
        builder = VisitOccurrenceSqlBuilder()
        
        # Test each column type
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE),
            "C.visit_start_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE),
            "C.visit_end_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT),
            "C.visit_concept_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION),
            "DATEDIFF(day, C.visit_start_date, C.visit_end_date)"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID),
            "C.visit_occurrence_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.AGE),
            "NULL"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.GENDER),
            "NULL"
        )

    def test_get_criteria_sql_basic(self):
        """Test get_criteria_sql with basic criteria."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("1=1", sql)  # Default where clause when no conditions

    def test_get_criteria_sql_with_options(self):
        """Test get_criteria_sql with builder options."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False
        )
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        sql = builder.get_criteria_sql_with_options(criteria, options)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("NULL as age", sql)
        self.assertIn("NULL as gender", sql)

    def test_get_criteria_sql_with_date_ranges(self):
        """Test get_criteria_sql with date range conditions."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01")
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE", sql)
        # Should have date conditions in where clause
        self.assertIn("C.visit_start_date", sql)
        self.assertIn("C.visit_end_date", sql)

    def test_get_criteria_sql_with_age_condition(self):
        """Test get_criteria_sql with age condition."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            age=NumericRange(op="gte", value=18, extent=65)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.person_id", sql)  # Age condition uses person_id

    def test_get_criteria_sql_with_provider_specialty(self):
        """Test get_criteria_sql with provider specialty condition."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("P.specialty_concept_id", sql)
        self.assertIn("12345", sql)

    def test_get_criteria_sql_with_provider_specialty_exclusion(self):
        """Test get_criteria_sql with provider specialty exclusion."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=True)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("not", sql)  # Should have 'not' for exclusion

    def test_get_criteria_sql_complex_scenario(self):
        """Test get_criteria_sql with multiple conditions."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            age=NumericRange(op="gte", value=18, extent=65),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("AND", sql)  # Should have multiple conditions joined with AND

    def test_embed_codeset_clause(self):
        """Test embed_codeset_clause method."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        # VisitOccurrence doesn't have codeset_id, so should return query with placeholder replaced
        self.assertEqual(clause, "SELECT * FROM table ")

    def test_resolve_select_clauses_basic(self):
        """Test resolve_select_clauses with basic criteria."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(visit_type_exclude=False)
        options = BuilderOptions()
        
        select_clause = builder.resolve_select_clauses(criteria, options)
        
        self.assertIn("C.visit_start_date as start_date", select_clause)
        self.assertIn("C.visit_end_date as end_date", select_clause)
        self.assertIn("C.visit_concept_id as domain_concept", select_clause)
        self.assertIn("C.visit_occurrence_id as visit_id", select_clause)

    def test_resolve_select_clauses_with_additional_columns(self):
        """Test resolve_select_clauses with additional columns."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(visit_type_exclude=False)
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        select_clause = builder.resolve_select_clauses(criteria, options)
        
        self.assertIn("C.visit_start_date as start_date", select_clause)
        self.assertIn("NULL as age", select_clause)
        self.assertIn("NULL as gender", select_clause)

    def test_resolve_join_clauses_no_joins(self):
        """Test resolve_join_clauses with no joins needed."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(visit_type_exclude=False)
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertEqual(join_clause, "")

    def test_resolve_join_clauses_with_provider_specialty(self):
        """Test resolve_join_clauses with provider specialty join."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertTrue(any("JOIN @cdm_database_schema.PROVIDER P" in clause for clause in join_clause))
        self.assertTrue(any("C.provider_id = P.provider_id" in clause for clause in join_clause))

    def test_resolve_join_clauses_with_provider_specialty_no_codeset_id(self):
        """Test resolve_join_clauses with provider specialty but no codeset_id."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=None, is_exclusion=False)
        )
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertEqual(join_clause, "")

    def test_resolve_where_clauses_basic(self):
        """Test resolve_where_clauses with basic criteria."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(visit_type_exclude=False)
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertEqual(where_clause, "1=1")

    def test_resolve_where_clauses_with_date_ranges(self):
        """Test resolve_where_clauses with date range conditions."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01")
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertIn("C.visit_start_date", where_clause)
        self.assertIn("C.visit_end_date", where_clause)
        # Should have multiple conditions
        self.assertGreater(len(where_clause), 1)

    def test_resolve_where_clauses_with_age_condition(self):
        """Test resolve_where_clauses with age condition."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            age=NumericRange(op="gte", value=18, extent=65)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.person_id" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_provider_specialty(self):
        """Test resolve_where_clauses with provider specialty condition."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("12345" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_provider_specialty_exclusion(self):
        """Test resolve_where_clauses with provider specialty exclusion."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=True)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("not" in clause for clause in where_clause))

    def test_resolve_where_clauses_complex_scenario(self):
        """Test resolve_where_clauses with multiple conditions."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            age=NumericRange(op="gte", value=18, extent=65),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertIn("C.visit_start_date", where_clause)
        self.assertIn("C.visit_end_date", where_clause)
        self.assertTrue(any("C.person_id" in clause for clause in where_clause))
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        # Should have multiple AND conditions
        self.assertGreater(where_clause.count("AND"), 2)

    def test_resolve_ordinal_expression(self):
        """Test resolve_ordinal_expression method."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(visit_type_exclude=False)
        options = BuilderOptions()
        
        ordinal_expression = builder.resolve_ordinal_expression(criteria, options)
        
        # VisitOccurrence doesn't have a 'first' field, so no ordering
        self.assertEqual(ordinal_expression, "")

    def test_sql_generation_edge_cases(self):
        """Test SQL generation with edge cases."""
        builder = VisitOccurrenceSqlBuilder()
        
        # Test with None values
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            occurrence_start_date=None,
            occurrence_end_date=None,
            age=None,
            provider_specialty_cs=None
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE 1=1", sql)
        self.assertNotIn("JOIN", sql)

    def test_sql_generation_with_empty_concept_lists(self):
        """Test SQL generation with empty concept lists."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            gender=[],
            visit_type=[],
            provider_specialty=[]
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE C", sql)
        self.assertIn("WHERE 1=1", sql)

    def test_sql_template_placeholder_replacement(self):
        """Test that all placeholders are properly replaced in SQL template."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(
            visit_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        # All placeholders should be replaced
        self.assertNotIn("@selectClause", sql)
        self.assertNotIn("@joinClause", sql)
        self.assertNotIn("@whereClause", sql)
        self.assertNotIn("@ordinalExpression", sql)
        
        # Should have actual content
        self.assertIn("C.visit_start_date as start_date", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("C.visit_start_date", sql)


class TestObservationSqlBuilder(unittest.TestCase):
    """Test ObservationSqlBuilder class."""

    def test_observation_sql_builder_initialization(self):
        """Test basic initialization of ObservationSqlBuilder."""
        builder = ObservationSqlBuilder()
        self.assertIsNotNone(builder)

    def test_get_query_template(self):
        """Test get_query_template method."""
        builder = ObservationSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@cdm_database_schema.OBSERVATION", template)

    def test_get_default_columns(self):
        """Test get_default_columns method."""
        builder = ObservationSqlBuilder()
        columns = builder.get_default_columns()
        
        expected_columns = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.VISIT_ID
        }
        self.assertEqual(columns, expected_columns)

    def test_get_table_column_for_criteria_column(self):
        """Test get_table_column_for_criteria_column method."""
        builder = ObservationSqlBuilder()
        
        # Test each column type
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE),
            "C.observation_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE),
            "C.observation_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT),
            "C.observation_concept_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION),
            "NULL"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID),
            "C.visit_occurrence_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.AGE),
            "C.value_as_string"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.GENDER),
            "NULL"
        )

    def test_get_criteria_sql_basic(self):
        """Test get_criteria_sql with basic criteria."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("ORDER BY C.observation_date ASC", sql)

    def test_get_criteria_sql_with_options(self):
        """Test get_criteria_sql with builder options."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False
        )
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        sql = builder.get_criteria_sql_with_options(criteria, options)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.value_as_string as age", sql)
        self.assertIn("NULL as gender", sql)

    def test_get_criteria_sql_with_date_ranges(self):
        """Test get_criteria_sql with date range conditions."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01")
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        # Should have date conditions in where clause
        self.assertIn("C.observation_date", sql)

    def test_get_criteria_sql_with_age_condition(self):
        """Test get_criteria_sql with age condition."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            age=NumericRange(op="gte", value=18, extent=65)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.person_id", sql)  # Age condition uses person_id

    def test_get_criteria_sql_with_value_as_string(self):
        """Test get_criteria_sql with value as string condition."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            value_as_string=TextFilter(text="normal", op="eq")
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.value_as_string", sql)

    def test_get_criteria_sql_with_provider_specialty(self):
        """Test get_criteria_sql with provider specialty condition."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("P.specialty_concept_id", sql)
        self.assertIn("12345", sql)

    def test_get_criteria_sql_with_provider_specialty_exclusion(self):
        """Test get_criteria_sql with provider specialty exclusion."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=True)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("not", sql)  # Should have 'not' for exclusion

    def test_get_criteria_sql_with_codeset_id(self):
        """Test get_criteria_sql with codeset ID."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            codeset_id=12345
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.observation_concept_id", sql)
        self.assertIn("12345", sql)

    def test_get_criteria_sql_complex_scenario(self):
        """Test get_criteria_sql with multiple conditions."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            age=NumericRange(op="gte", value=18, extent=65),
            value_as_string=TextFilter(text="normal", op="eq"),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False),
            codeset_id=67890
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("AND", sql)  # Should have multiple conditions joined with AND

    def test_embed_codeset_clause(self):
        """Test embed_codeset_clause method."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            codeset_id=12345,
            first=True,
            observation_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        self.assertIn("C.observation_concept_id", clause)
        self.assertIn("12345", clause)

    def test_embed_codeset_clause_no_codeset(self):
        """Test embed_codeset_clause with no codeset ID."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        self.assertEqual(clause, "SELECT * FROM table ")

    def test_resolve_select_clauses_basic(self):
        """Test resolve_select_clauses with basic criteria."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=True, observation_type_exclude=False)
        options = BuilderOptions()
        
        select_clause = builder.resolve_select_clauses(criteria, options)
        
        self.assertIn("C.observation_date as start_date", select_clause)
        self.assertIn("C.observation_date as end_date", select_clause)
        self.assertIn("C.observation_concept_id as domain_concept", select_clause)
        self.assertIn("C.visit_occurrence_id as visit_id", select_clause)

    def test_resolve_select_clauses_with_additional_columns(self):
        """Test resolve_select_clauses with additional columns."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=True, observation_type_exclude=False)
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        select_clause = builder.resolve_select_clauses(criteria, options)
        
        self.assertIn("C.observation_date as start_date", select_clause)
        self.assertIn("C.value_as_string as age", select_clause)
        self.assertIn("NULL as gender", select_clause)

    def test_resolve_join_clauses_no_joins(self):
        """Test resolve_join_clauses with no joins needed."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=True, observation_type_exclude=False)
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertEqual(join_clause, "")

    def test_resolve_join_clauses_with_provider_specialty(self):
        """Test resolve_join_clauses with provider specialty join."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertTrue(any("JOIN @cdm_database_schema.PROVIDER P" in clause for clause in join_clause))
        self.assertTrue(any("C.provider_id = P.provider_id" in clause for clause in join_clause))

    def test_resolve_join_clauses_with_provider_specialty_no_codeset_id(self):
        """Test resolve_join_clauses with provider specialty but no codeset_id."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=None, is_exclusion=False)
        )
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertEqual(join_clause, [])

    def test_resolve_where_clauses_basic(self):
        """Test resolve_where_clauses with basic criteria."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=True, observation_type_exclude=False)
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertEqual(where_clause, ["1=1"])

    def test_resolve_where_clauses_with_date_ranges(self):
        """Test resolve_where_clauses with date range conditions."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01")
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.observation_date" in clause for clause in where_clause))
        # Should have multiple conditions
        self.assertGreater(len(where_clause), 1)

    def test_resolve_where_clauses_with_age_condition(self):
        """Test resolve_where_clauses with age condition."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            age=NumericRange(op="gte", value=18, extent=65)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.person_id" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_value_as_string(self):
        """Test resolve_where_clauses with value as string condition."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            value_as_string=TextFilter(text="normal", op="eq")
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.value_as_string" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_provider_specialty(self):
        """Test resolve_where_clauses with provider specialty condition."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("12345" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_provider_specialty_exclusion(self):
        """Test resolve_where_clauses with provider specialty exclusion."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=True)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("not" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_codeset_id(self):
        """Test resolve_where_clauses with codeset ID."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            codeset_id=12345
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.observation_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("12345" in clause for clause in where_clause))

    def test_resolve_where_clauses_complex_scenario(self):
        """Test resolve_where_clauses with multiple conditions."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            age=NumericRange(op="gte", value=18, extent=65),
            value_as_string=TextFilter(text="normal", op="eq"),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False),
            codeset_id=67890
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.observation_date" in clause for clause in where_clause))
        self.assertTrue(any("C.person_id" in clause for clause in where_clause))
        self.assertTrue(any("C.value_as_string" in clause for clause in where_clause))
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("C.observation_concept_id" in clause for clause in where_clause))
        # Should have multiple AND conditions
        self.assertGreater(where_clause.count("AND"), 4)

    def test_resolve_ordinal_expression_with_first(self):
        """Test resolve_ordinal_expression with first=True."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=True, observation_type_exclude=False)
        options = BuilderOptions()
        
        ordinal_expression = builder.resolve_ordinal_expression(criteria, options)
        
        self.assertEqual(ordinal_expression, "ORDER BY C.observation_date ASC")

    def test_resolve_ordinal_expression_without_first(self):
        """Test resolve_ordinal_expression with first=False."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=False, observation_type_exclude=False)
        options = BuilderOptions()
        
        ordinal_expression = builder.resolve_ordinal_expression(criteria, options)
        
        self.assertEqual(ordinal_expression, "")

    def test_sql_generation_edge_cases(self):
        """Test SQL generation with edge cases."""
        builder = ObservationSqlBuilder()
        
        # Test with None values
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            occurrence_start_date=None,
            occurrence_end_date=None,
            age=None,
            value_as_string=None,
            provider_specialty_cs=None,
            codeset_id=None
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE 1=1", sql)
        self.assertNotIn("JOIN", sql)

    def test_sql_generation_with_empty_concept_lists(self):
        """Test SQL generation with empty concept lists."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            gender=[],
            observation_type=[],
            provider_specialty=[]
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.OBSERVATION C", sql)
        self.assertIn("WHERE 1=1", sql)

    def test_sql_template_placeholder_replacement(self):
        """Test that all placeholders are properly replaced in SQL template."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False),
            codeset_id=67890
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        # All placeholders should be replaced
        self.assertNotIn("@selectClause", sql)
        self.assertNotIn("@joinClause", sql)
        self.assertNotIn("@whereClause", sql)
        self.assertNotIn("@ordinalExpression", sql)
        
        # Should have actual content
        self.assertIn("C.observation_date as start_date", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("C.observation_date", sql)
        self.assertIn("ORDER BY C.observation_date ASC", sql)


class TestMeasurementSqlBuilder(unittest.TestCase):
    """Test MeasurementSqlBuilder class."""

    def test_measurement_sql_builder_initialization(self):
        """Test basic initialization of MeasurementSqlBuilder."""
        builder = MeasurementSqlBuilder()
        self.assertIsNotNone(builder)

    def test_get_query_template(self):
        """Test get_query_template method."""
        builder = MeasurementSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@cdm_database_schema.MEASUREMENT", template)

    def test_get_default_columns(self):
        """Test get_default_columns method."""
        builder = MeasurementSqlBuilder()
        columns = builder.get_default_columns()
        
        expected_columns = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.VISIT_ID
        }
        self.assertEqual(columns, expected_columns)

    def test_get_table_column_for_criteria_column(self):
        """Test get_table_column_for_criteria_column method."""
        builder = MeasurementSqlBuilder()
        
        # Test each column type
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE),
            "C.measurement_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE),
            "C.measurement_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT),
            "C.measurement_concept_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION),
            "NULL"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID),
            "C.visit_occurrence_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.AGE),
            "C.value_as_number"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.GENDER),
            "NULL"
        )

    def test_get_criteria_sql_basic(self):
        """Test get_criteria_sql with basic criteria."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("ORDER BY C.measurement_date ASC", sql)

    def test_get_criteria_sql_with_options(self):
        """Test get_criteria_sql with builder options."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False
        )
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        sql = builder.get_criteria_sql_with_options(criteria, options)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.value_as_number as age", sql)
        self.assertIn("NULL as gender", sql)

    def test_get_criteria_sql_with_date_ranges(self):
        """Test get_criteria_sql with date range conditions."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01")
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        # Should have date conditions in where clause
        self.assertIn("C.measurement_date", sql)

    def test_get_criteria_sql_with_age_condition(self):
        """Test get_criteria_sql with age condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            age=NumericRange(op="gte", value=18, extent=65)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.person_id", sql)  # Age condition uses person_id

    def test_get_criteria_sql_with_value_as_number(self):
        """Test get_criteria_sql with value as number condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            value_as_number=NumericRange(op="gte", value=100, extent=200)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.value_as_number", sql)

    def test_get_criteria_sql_with_value_as_string(self):
        """Test get_criteria_sql with value as string condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            value_as_string=TextFilter(text="normal", op="eq")
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.value_as_string", sql)

    def test_get_criteria_sql_with_range_low(self):
        """Test get_criteria_sql with range low condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            range_low=NumericRange(op="gte", value=50, extent=100)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.range_low", sql)

    def test_get_criteria_sql_with_range_high(self):
        """Test get_criteria_sql with range high condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            range_high=NumericRange(op="lt", value=200, extent=300)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.range_high", sql)

    def test_get_criteria_sql_with_provider_specialty(self):
        """Test get_criteria_sql with provider specialty condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("P.specialty_concept_id", sql)
        self.assertIn("12345", sql)

    def test_get_criteria_sql_with_provider_specialty_exclusion(self):
        """Test get_criteria_sql with provider specialty exclusion."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=True)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("not", sql)  # Should have 'not' for exclusion

    def test_get_criteria_sql_with_codeset_id(self):
        """Test get_criteria_sql with codeset ID."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            codeset_id=12345
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("C.measurement_concept_id", sql)
        self.assertIn("12345", sql)

    def test_get_criteria_sql_complex_scenario(self):
        """Test get_criteria_sql with multiple conditions."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            age=NumericRange(op="gte", value=18, extent=65),
            value_as_number=NumericRange(op="gte", value=100, extent=200),
            value_as_string=TextFilter(text="normal", op="eq"),
            range_low=NumericRange(op="gte", value=50, extent=100),
            range_high=NumericRange(op="lt", value=200, extent=300),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False),
            codeset_id=67890
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("AND", sql)  # Should have multiple conditions joined with AND

    def test_embed_codeset_clause(self):
        """Test embed_codeset_clause method."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            codeset_id=12345,
            first=True,
            measurement_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        self.assertIn("C.measurement_concept_id", clause)
        self.assertIn("12345", clause)

    def test_embed_codeset_clause_no_codeset(self):
        """Test embed_codeset_clause with no codeset ID."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        self.assertEqual(clause, "SELECT * FROM table ")

    def test_resolve_select_clauses_basic(self):
        """Test resolve_select_clauses with basic criteria."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(first=True, measurement_type_exclude=False)
        options = BuilderOptions()
        
        select_clause = builder.resolve_select_clauses(criteria, options)
        
        self.assertIn("C.measurement_date as start_date", select_clause)
        self.assertIn("C.measurement_date as end_date", select_clause)
        self.assertIn("C.measurement_concept_id as domain_concept", select_clause)
        self.assertIn("C.visit_occurrence_id as visit_id", select_clause)

    def test_resolve_select_clauses_with_additional_columns(self):
        """Test resolve_select_clauses with additional columns."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(first=True, measurement_type_exclude=False)
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        select_clause = builder.resolve_select_clauses(criteria, options)
        
        self.assertIn("C.measurement_date as start_date", select_clause)
        self.assertIn("C.value_as_number as age", select_clause)
        self.assertIn("NULL as gender", select_clause)

    def test_resolve_join_clauses_no_joins(self):
        """Test resolve_join_clauses with no joins needed."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(first=True, measurement_type_exclude=False)
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertEqual(join_clause, [])

    def test_resolve_join_clauses_with_provider_specialty(self):
        """Test resolve_join_clauses with provider specialty join."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertTrue(any("JOIN @cdm_database_schema.PROVIDER P" in clause for clause in join_clause))
        self.assertTrue(any("C.provider_id = P.provider_id" in clause for clause in join_clause))

    def test_resolve_join_clauses_with_provider_specialty_no_codeset_id(self):
        """Test resolve_join_clauses with provider specialty but no codeset_id."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=None, is_exclusion=False)
        )
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertEqual(join_clause, [])

    def test_resolve_where_clauses_basic(self):
        """Test resolve_where_clauses with basic criteria."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(first=True, measurement_type_exclude=False)
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertEqual(where_clause, ["1=1"])

    def test_resolve_where_clauses_with_date_ranges(self):
        """Test resolve_where_clauses with date range conditions."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01")
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.measurement_date" in clause for clause in where_clause))
        # Should have multiple clauses for date ranges
        self.assertGreater(len(where_clause), 1)

    def test_resolve_where_clauses_with_age_condition(self):
        """Test resolve_where_clauses with age condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            age=NumericRange(op="gte", value=18, extent=65)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.person_id" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_value_as_number(self):
        """Test resolve_where_clauses with value as number condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            value_as_number=NumericRange(op="gte", value=100, extent=200)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.value_as_number" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_value_as_string(self):
        """Test resolve_where_clauses with value as string condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            value_as_string=TextFilter(text="normal", op="eq")
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.value_as_string" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_range_low(self):
        """Test resolve_where_clauses with range low condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            range_low=NumericRange(op="gte", value=50, extent=100)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.range_low" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_range_high(self):
        """Test resolve_where_clauses with range high condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            range_high=NumericRange(op="lt", value=200, extent=300)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.range_high" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_provider_specialty(self):
        """Test resolve_where_clauses with provider specialty condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("12345" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_provider_specialty_exclusion(self):
        """Test resolve_where_clauses with provider specialty exclusion."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=True)
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("not" in clause for clause in where_clause))

    def test_resolve_where_clauses_with_codeset_id(self):
        """Test resolve_where_clauses with codeset ID."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            codeset_id=12345
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.measurement_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("12345" in clause for clause in where_clause))

    def test_resolve_where_clauses_complex_scenario(self):
        """Test resolve_where_clauses with multiple conditions."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            age=NumericRange(op="gte", value=18, extent=65),
            value_as_number=NumericRange(op="gte", value=100, extent=200),
            value_as_string=TextFilter(text="normal", op="eq"),
            range_low=NumericRange(op="gte", value=50, extent=100),
            range_high=NumericRange(op="lt", value=200, extent=300),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False),
            codeset_id=67890
        )
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertTrue(any("C.measurement_date" in clause for clause in where_clause))
        self.assertTrue(any("C.person_id" in clause for clause in where_clause))
        self.assertTrue(any("C.value_as_number" in clause for clause in where_clause))
        self.assertTrue(any("C.value_as_string" in clause for clause in where_clause))
        self.assertTrue(any("C.range_low" in clause for clause in where_clause))
        self.assertTrue(any("C.range_high" in clause for clause in where_clause))
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        self.assertTrue(any("C.measurement_concept_id" in clause for clause in where_clause))
        # Should have multiple conditions
        self.assertGreater(len(where_clause), 6)

    def test_resolve_ordinal_expression_with_first(self):
        """Test resolve_ordinal_expression with first=True."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(first=True, measurement_type_exclude=False)
        options = BuilderOptions()
        
        ordinal_expression = builder.resolve_ordinal_expression(criteria, options)
        
        self.assertEqual(ordinal_expression, "ORDER BY C.measurement_date ASC")

    def test_resolve_ordinal_expression_without_first(self):
        """Test resolve_ordinal_expression with first=False."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(first=False, measurement_type_exclude=False)
        options = BuilderOptions()
        
        ordinal_expression = builder.resolve_ordinal_expression(criteria, options)
        
        self.assertEqual(ordinal_expression, "")

    def test_sql_generation_edge_cases(self):
        """Test SQL generation with edge cases."""
        builder = MeasurementSqlBuilder()
        
        # Test with None values
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            occurrence_start_date=None,
            occurrence_end_date=None,
            age=None,
            value_as_number=None,
            value_as_string=None,
            range_low=None,
            range_high=None,
            provider_specialty_cs=None,
            codeset_id=None
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE 1=1", sql)
        self.assertNotIn("JOIN", sql)

    def test_sql_generation_with_empty_concept_lists(self):
        """Test SQL generation with empty concept lists."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            gender=[],
            measurement_type=[],
            operator=[],
            unit=[],
            provider_specialty=[]
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT C", sql)
        self.assertIn("WHERE 1=1", sql)

    def test_sql_template_placeholder_replacement(self):
        """Test that all placeholders are properly replaced in SQL template."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01"),
            provider_specialty_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False),
            codeset_id=67890
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        # All placeholders should be replaced
        self.assertNotIn("@selectClause", sql)
        self.assertNotIn("@joinClause", sql)
        self.assertNotIn("@whereClause", sql)
        self.assertNotIn("@ordinalExpression", sql)
        
        # Should have actual content
        self.assertIn("C.measurement_date as start_date", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER P", sql)
        self.assertIn("C.measurement_date", sql)
        self.assertIn("ORDER BY C.measurement_date ASC", sql)


class TestDeviceExposureSqlBuilder(unittest.TestCase):
    """Test DeviceExposureSqlBuilder class."""

    def test_device_exposure_sql_builder_initialization(self):
        """Test basic initialization of DeviceExposureSqlBuilder."""
        builder = DeviceExposureSqlBuilder()
        self.assertIsNotNone(builder)

    def test_get_query_template(self):
        """Test get_query_template method."""
        builder = DeviceExposureSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@cdm_database_schema.DEVICE_EXPOSURE", template)

    def test_get_default_columns(self):
        """Test get_default_columns method."""
        builder = DeviceExposureSqlBuilder()
        columns = builder.get_default_columns()
        
        expected_columns = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.VISIT_ID
        }
        self.assertEqual(columns, expected_columns)

    def test_get_table_column_for_criteria_column(self):
        """Test get_table_column_for_criteria_column method."""
        builder = DeviceExposureSqlBuilder()
        
        # Test each column type
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE),
            "C.device_exposure_start_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE),
            "C.device_exposure_end_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT),
            "C.device_concept_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION),
            "DATEDIFF(day, C.device_exposure_start_date, C.device_exposure_end_date)"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID),
            "C.visit_occurrence_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.AGE),
            "C.unique_device_id"
        )

    def test_get_criteria_sql_basic(self):
        """Test get_criteria_sql with basic criteria."""
        builder = DeviceExposureSqlBuilder()
        criteria = DeviceExposure(
            first=True,
            device_type_exclude=False
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.DEVICE_EXPOSURE C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("ORDER BY C.device_exposure_start_date ASC", sql)

    def test_embed_codeset_clause(self):
        """Test embed_codeset_clause method."""
        builder = DeviceExposureSqlBuilder()
        criteria = DeviceExposure(
            codeset_id=12345,
            first=True,
            device_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        self.assertIn("C.device_concept_id", clause)
        self.assertIn("12345", clause)


class TestSpecimenSqlBuilder(unittest.TestCase):
    """Test SpecimenSqlBuilder class."""

    def test_specimen_sql_builder_initialization(self):
        """Test basic initialization of SpecimenSqlBuilder."""
        builder = SpecimenSqlBuilder()
        self.assertIsNotNone(builder)

    def test_get_query_template(self):
        """Test get_query_template method."""
        builder = SpecimenSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@cdm_database_schema.SPECIMEN", template)

    def test_get_default_columns(self):
        """Test get_default_columns method."""
        builder = SpecimenSqlBuilder()
        columns = builder.get_default_columns()
        
        expected_columns = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.DOMAIN_CONCEPT
        }
        self.assertEqual(columns, expected_columns)

    def test_get_table_column_for_criteria_column(self):
        """Test get_table_column_for_criteria_column method."""
        builder = SpecimenSqlBuilder()
        
        # Test each column type
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE),
            "C.specimen_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE),
            "C.specimen_date"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT),
            "C.specimen_concept_id"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION),
            "NULL"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID),
            "NULL"
        )
        self.assertEqual(
            builder.get_table_column_for_criteria_column(CriteriaColumn.AGE),
            "C.quantity"
        )

    def test_get_criteria_sql_basic(self):
        """Test get_criteria_sql with basic criteria."""
        builder = SpecimenSqlBuilder()
        criteria = Specimen(
            first=True,
            specimen_type_exclude=False
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM @cdm_database_schema.SPECIMEN C", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("ORDER BY C.specimen_date ASC", sql)

    def test_embed_codeset_clause(self):
        """Test embed_codeset_clause method."""
        builder = SpecimenSqlBuilder()
        criteria = Specimen(
            codeset_id=12345,
            first=True,
            specimen_type_exclude=False
        )
        
        clause = builder.embed_codeset_clause("SELECT * FROM table @codesetClause", criteria)
        self.assertIn("C.specimen_concept_id", clause)
        self.assertIn("12345", clause)


class TestNewSqlBuildersIntegration(unittest.TestCase):
    """Test integration between new SQL builders."""

    def test_all_new_builders_importable(self):
        """Test that all new builders can be imported."""
        from circe.cohortdefinition.builders import (
            DeathSqlBuilder, VisitOccurrenceSqlBuilder, ObservationSqlBuilder,
            MeasurementSqlBuilder, DeviceExposureSqlBuilder, SpecimenSqlBuilder
        )
        
        # Test that all builders are importable
        self.assertTrue(DeathSqlBuilder is not None)
        self.assertTrue(VisitOccurrenceSqlBuilder is not None)
        self.assertTrue(ObservationSqlBuilder is not None)
        self.assertTrue(MeasurementSqlBuilder is not None)
        self.assertTrue(DeviceExposureSqlBuilder is not None)
        self.assertTrue(SpecimenSqlBuilder is not None)

    def test_builder_options_with_new_builders(self):
        """Test BuilderOptions with new builders."""
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.VISIT_ID, CriteriaColumn.DURATION]
        
        builders = [
            DeathSqlBuilder(),
            VisitOccurrenceSqlBuilder(),
            ObservationSqlBuilder(),
            MeasurementSqlBuilder(),
            DeviceExposureSqlBuilder(),
            SpecimenSqlBuilder()
        ]
        
        for builder in builders:
            # Test that all builders can handle the options
            self.assertIsNotNone(builder)
            # Test that they have the required methods
            self.assertTrue(hasattr(builder, 'get_criteria_sql'))
            self.assertTrue(hasattr(builder, 'get_default_columns'))
            self.assertTrue(hasattr(builder, 'get_query_template'))

    def test_sql_template_structure_consistency(self):
        """Test that all new builders have consistent SQL template structure."""
        builders = [
            DeathSqlBuilder(),
            VisitOccurrenceSqlBuilder(),
            ObservationSqlBuilder(),
            MeasurementSqlBuilder(),
            DeviceExposureSqlBuilder(),
            SpecimenSqlBuilder()
        ]
        
        for builder in builders:
            template = builder.get_query_template()
            
            # All templates should have these placeholders
            self.assertIn("@selectClause", template)
            self.assertIn("@joinClause", template)
            self.assertIn("@whereClause", template)
            self.assertIn("@ordinalExpression", template)
            
            # All templates should have basic SQL structure
            self.assertIn("SELECT", template)
            self.assertIn("FROM", template)
            self.assertIn("WHERE", template)
            
            # All templates should reference the CDM database schema
            self.assertIn("@cdm_database_schema", template)

    def test_criteria_column_consistency_across_new_builders(self):
        """Test that criteria columns are consistent across new builders."""
        builders = [
            DeathSqlBuilder(),
            VisitOccurrenceSqlBuilder(),
            ObservationSqlBuilder(),
            MeasurementSqlBuilder(),
            DeviceExposureSqlBuilder(),
            SpecimenSqlBuilder()
        ]
        
        for builder in builders:
            columns = builder.get_default_columns()
            
            # All builders should have at least START_DATE and END_DATE
            self.assertIn(CriteriaColumn.START_DATE, columns)
            self.assertIn(CriteriaColumn.END_DATE, columns)
            self.assertIn(CriteriaColumn.DOMAIN_CONCEPT, columns)
            
            # Test that column mapping works for all builders
            for column in columns:
                table_column = builder.get_table_column_for_criteria_column(column)
                self.assertIsNotNone(table_column)
                self.assertIsInstance(table_column, str)


if __name__ == '__main__':
    unittest.main()
