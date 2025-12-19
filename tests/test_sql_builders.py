"""
Tests for SQL Builders

This module contains comprehensive tests for all SQL builders
that generate SQL queries from cohort definition criteria.

GUARD RAIL: These tests ensure 1:1 compatibility with Java CIRCE-BE functionality.
Any changes must maintain compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

import unittest
import sys
import os
from typing import Set, List, Optional
from unittest.mock import Mock

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from circe.cohortdefinition.builders import (
    DeathSqlBuilder, VisitOccurrenceSqlBuilder, ObservationSqlBuilder,
    MeasurementSqlBuilder, DeviceExposureSqlBuilder, SpecimenSqlBuilder,
    DoseEraSqlBuilder, ObservationPeriodSqlBuilder, PayerPlanPeriodSqlBuilder,
    VisitDetailSqlBuilder, LocationRegionSqlBuilder
)
from circe.cohortdefinition.builders.utils import BuilderOptions, CriteriaColumn
from circe.cohortdefinition.criteria import (
    Death, VisitOccurrence, Observation, Measurement, DeviceExposure, Specimen,
    DoseEra, ObservationPeriod, PayerPlanPeriod, VisitDetail, LocationRegion
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
        
        self.assertEqual(join_clause, [])

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
        
        self.assertEqual(join_clause, [])

    def test_resolve_where_clauses_basic(self):
        """Test resolve_where_clauses with basic criteria."""
        builder = VisitOccurrenceSqlBuilder()
        criteria = VisitOccurrence(visit_type_exclude=False)
        options = BuilderOptions()
        
        where_clause = builder.resolve_where_clauses(criteria, options)
        
        self.assertEqual(where_clause, ["1=1"])

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
        
        # Check that the clauses contain the expected column references
        self.assertTrue(any("C.visit_start_date" in clause for clause in where_clause))
        self.assertTrue(any("C.visit_end_date" in clause for clause in where_clause))
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
        
        # Check that the clauses contain the expected column references
        self.assertTrue(any("C.visit_start_date" in clause for clause in where_clause))
        self.assertTrue(any("C.visit_end_date" in clause for clause in where_clause))
        self.assertTrue(any("C.person_id" in clause for clause in where_clause))
        self.assertTrue(any("P.specialty_concept_id" in clause for clause in where_clause))
        # Should have multiple conditions
        self.assertGreater(len(where_clause), 2)

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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("C.ordinal = 1", sql)
        self.assertIn("row_number() over", sql.lower())

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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("WHERE", sql)
        # Additional columns are added to outer SELECT
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("WHERE", sql)
        # Should have date conditions in where clause (uses C.start_date/end_date)
        self.assertIn("C.start_date", sql)

    def test_get_criteria_sql_with_age_condition(self):
        """Test get_criteria_sql with age condition."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            age=NumericRange(op="gte", value=18, extent=65)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("WHERE", sql)
        # Age condition uses C.start_date and P.year_of_birth
        self.assertIn("P.year_of_birth", sql)

    def test_get_criteria_sql_with_value_as_string(self):
        """Test get_criteria_sql with value as string condition."""
        builder = ObservationSqlBuilder()
        criteria = Observation(
            first=True,
            observation_type_exclude=False,
            value_as_string=TextFilter(text="normal", op="eq")
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("WHERE", sql)
        # ObservationSqlBuilder uses PR alias for PROVIDER (to avoid conflict with PERSON alias P)
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR", sql)
        self.assertIn("PR.specialty_concept_id", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("WHERE", sql)
        # ObservationSqlBuilder uses PR alias for PROVIDER (to avoid conflict with PERSON alias P)
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR", sql)
        self.assertIn("PR.specialty_concept_id", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("o.observation_concept_id", sql)
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
    
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("WHERE", sql)
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql)  # Age requires PERSON join
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
        self.assertIn("o.observation_concept_id", clause)
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
        
        self.assertIn("o.observation_date as start_date", select_clause)
        self.assertIn("DATEADD(day,1,o.observation_date) as end_date", select_clause)
        self.assertIn("o.person_id", select_clause)
        self.assertIn("o.observation_id", select_clause)

    def test_resolve_select_clauses_with_additional_columns(self):
        """Test resolve_select_clauses with additional columns."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=True, observation_type_exclude=False)
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        select_clause = builder.resolve_select_clauses(criteria, options)
        
        # resolve_select_clauses now only returns inner query columns
        # Additional columns are handled by get_additional_columns separately
        self.assertIn("o.observation_date as start_date", select_clause)
        self.assertIn("o.person_id", select_clause)

    def test_resolve_join_clauses_no_joins(self):
        """Test resolve_join_clauses with no joins needed."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=True, observation_type_exclude=False)
        options = BuilderOptions()
        
        join_clause = builder.resolve_join_clauses(criteria, options)
        
        self.assertEqual(join_clause, [])

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
        
        self.assertTrue(any("JOIN @cdm_database_schema.PROVIDER PR" in clause for clause in join_clause))
        self.assertTrue(any("C.provider_id = PR.provider_id" in clause for clause in join_clause))

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
        
        self.assertEqual(where_clause, [])

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
        
        self.assertTrue(any("C.start_date" in clause or "C.end_date" in clause for clause in where_clause))
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
        
        self.assertTrue(any("C.start_date" in clause and "P.year_of_birth" in clause for clause in where_clause))

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
        
        # ObservationSqlBuilder uses PR alias for PROVIDER (to avoid conflict with PERSON alias P)
        self.assertTrue(any("PR.specialty_concept_id" in clause for clause in where_clause))
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
        
        # ObservationSqlBuilder uses PR alias for PROVIDER (to avoid conflict with PERSON alias P)
        self.assertTrue(any("PR.specialty_concept_id" in clause for clause in where_clause))
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
        
        # Codeset filtering is now handled via JOIN in the inner query, not in WHERE clause
        # So where_clause should be empty for just codeset_id
        self.assertEqual(where_clause, [])

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
        
        # Check for date conditions (uses C.start_date and C.end_date)
        self.assertTrue(any("C.start_date" in clause or "C.end_date" in clause for clause in where_clause))
        # Check for age condition (uses C.start_date and P.year_of_birth)
        self.assertTrue(any("P.year_of_birth" in clause for clause in where_clause))
        # Check for value_as_string
        self.assertTrue(any("C.value_as_string" in clause for clause in where_clause))
        # ObservationSqlBuilder uses PR alias for PROVIDER (to avoid conflict with PERSON alias P)
        self.assertTrue(any("PR.specialty_concept_id" in clause for clause in where_clause))
        # Note: codeset_id is now handled via JOIN, not WHERE clause
        # Should have multiple conditions (where_clause is a list of strings)
        self.assertGreater(len(where_clause), 3)

    def test_resolve_ordinal_expression_with_first(self):
        """Test resolve_ordinal_expression with first=True."""
        builder = ObservationSqlBuilder()
        criteria = Observation(first=True, observation_type_exclude=False)
        options = BuilderOptions()
        
        ordinal_expression = builder.resolve_ordinal_expression(criteria, options)
        
        # Now uses row_number() over with partition by person_id
        self.assertIn("row_number() over", ordinal_expression.lower())
        self.assertIn("o.person_id", ordinal_expression)
        self.assertIn("o.observation_date", ordinal_expression)

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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("C.ordinal = 1", sql)  # WHERE clause for first=True
        self.assertNotIn("JOIN @cdm_database_schema.PERSON", sql)  # No age condition, no PERSON join

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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.OBSERVATION o", sql)
        self.assertIn("C.ordinal = 1", sql)  # WHERE clause for first=True

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
        self.assertNotIn("@codesetClause", sql)
        
        # Should have actual content with new nested structure
        self.assertIn("o.observation_date as start_date", sql)
        self.assertIn("JOIN @cdm_database_schema.PROVIDER PR", sql)  # Uses PR alias
        self.assertIn("row_number() over", sql.lower())  # Uses row_number for first
        self.assertIn("C.ordinal = 1", sql)  # Filters by ordinal in outer WHERE


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
        
        # Check for nested structure with lowercase keywords
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        self.assertIn("ROW_NUMBER() OVER", sql)  # first=True generates ordinal

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
        
        # Check for nested structure
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        # Additional columns are in outer SELECT
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        self.assertIn("WHERE", sql)
        # Date conditions use C.start_date/C.end_date in outer query
        self.assertTrue("C.start_date" in sql or "C.end_date" in sql)

    def test_get_criteria_sql_with_age_condition(self):
        """Test get_criteria_sql with age condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            age=NumericRange(op="gte", value=18, extent=65)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        self.assertIn("WHERE", sql)
        # Age condition uses YEAR(C.start_date) in outer query
        self.assertIn("YEAR(C.start_date)", sql)

    def test_get_criteria_sql_with_value_as_number(self):
        """Test get_criteria_sql with value as number condition."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(
            first=True,
            measurement_type_exclude=False,
            value_as_number=NumericRange(op="gte", value=100, extent=200)
        )
        
        sql = builder.get_criteria_sql(criteria)
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        self.assertIn("WHERE", sql)
        # Provider now uses PR alias
        self.assertIn("JOIN @cdm_database_schema.PROVIDER PR", sql)
        self.assertIn("PR.specialty_concept_id", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        self.assertIn("WHERE", sql)
        # Provider now uses PR alias
        self.assertIn("JOIN @cdm_database_schema.PROVIDER PR", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        # Codeset filtering is via JOIN in inner query
        self.assertIn("JOIN #Codesets cs", sql)
        self.assertIn("m.measurement_concept_id", sql)
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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        self.assertIn("WHERE", sql)
        # Provider uses PR alias
        self.assertIn("JOIN @cdm_database_schema.PROVIDER PR", sql)
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
        self.assertIn("m.measurement_concept_id", clause)  # Use m. prefix in inner query
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
        
        # Inner query uses m. prefix
        self.assertIn("m.measurement_date as start_date", select_clause)
        self.assertIn("m.person_id", select_clause)
        self.assertIn("m.measurement_id", select_clause)
        self.assertIn("m.measurement_concept_id", select_clause)
        self.assertIn("m.visit_occurrence_id", select_clause)

    def test_resolve_select_clauses_with_additional_columns(self):
        """Test resolve_select_clauses with additional columns."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(first=True, measurement_type_exclude=False)
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        
        select_clause = builder.resolve_select_clauses(criteria, options)
        
        # resolve_select_clauses returns inner query columns (m. prefix)
        # Additional columns are handled elsewhere in the template
        self.assertIn("m.measurement_date as start_date", select_clause)
        self.assertIn("m.value_as_number", select_clause)

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
        
        # Provider now uses PR alias to avoid conflict with PERSON P
        self.assertTrue(any("JOIN @cdm_database_schema.PROVIDER PR" in clause for clause in join_clause))
        self.assertTrue(any("C.provider_id = PR.provider_id" in clause for clause in join_clause))

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
        
        self.assertEqual(where_clause, [])

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
        
        # Now uses C.start_date and C.end_date (from outer query)
        self.assertTrue(any("C.start_date" in clause or "C.end_date" in clause for clause in where_clause))
        # Should have multiple clauses for date ranges
        self.assertGreater(len(where_clause), 0)

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
        
        # Age condition uses YEAR(C.start_date) - P.year_of_birth
        self.assertTrue(any("YEAR(C.start_date)" in clause for clause in where_clause))

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
        
        # Provider now uses PR alias to avoid conflict with PERSON (P)
        self.assertTrue(any("PR.specialty_concept_id" in clause for clause in where_clause))
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
        
        # Provider now uses PR alias
        self.assertTrue(any("PR.specialty_concept_id" in clause for clause in where_clause))
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
        
        # Codeset filtering is now handled via JOIN in inner query, not WHERE clause
        self.assertEqual(where_clause, [])

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
        
        # Date conditions use C.start_date/C.end_date in outer query
        self.assertTrue(any("C.start_date" in clause or "C.end_date" in clause for clause in where_clause))
        # Age conditions use YEAR(C.start_date)
        self.assertTrue(any("YEAR(C.start_date)" in clause for clause in where_clause))
        self.assertTrue(any("C.value_as_number" in clause for clause in where_clause))
        self.assertTrue(any("C.value_as_string" in clause for clause in where_clause))
        self.assertTrue(any("C.range_low" in clause for clause in where_clause))
        self.assertTrue(any("C.range_high" in clause for clause in where_clause))
        # Provider now uses PR alias to avoid conflict with PERSON P
        self.assertTrue(any("PR.specialty_concept_id" in clause for clause in where_clause))
        # codeset_id is now handled via JOIN in inner query, not WHERE clause
        # Should have multiple conditions
        self.assertGreater(len(where_clause), 6)

    def test_resolve_ordinal_expression_with_first(self):
        """Test resolve_ordinal_expression with first=True."""
        builder = MeasurementSqlBuilder()
        criteria = Measurement(first=True, measurement_type_exclude=False)
        options = BuilderOptions()
        
        ordinal_expression = builder.resolve_ordinal_expression(criteria, options)
        
        # Now uses ROW_NUMBER() window function like ObservationSqlBuilder
        self.assertIn("ROW_NUMBER() OVER", ordinal_expression)
        self.assertIn("m.person_id", ordinal_expression)
        self.assertIn("m.measurement_date", ordinal_expression)

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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        # With first=True, generates ROW_NUMBER() OVER
        self.assertIn("ROW_NUMBER() OVER", sql)
        # No JOINs to PERSON or PROVIDER since no age or provider conditions
        self.assertNotIn("JOIN @cdm_database_schema.PERSON", sql)
        self.assertNotIn("JOIN @cdm_database_schema.PROVIDER", sql)

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
        
        self.assertIn("select", sql.lower())
        self.assertIn("FROM @cdm_database_schema.MEASUREMENT m", sql)
        # With first=True, generates ROW_NUMBER() OVER
        self.assertIn("ROW_NUMBER() OVER", sql)

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
        
        # All placeholders should be replaced (now uses @codesetClause, @additionalColumns)
        self.assertNotIn("@selectClause", sql)
        self.assertNotIn("@joinClause", sql)
        self.assertNotIn("@whereClause", sql)
        self.assertNotIn("@ordinalExpression", sql)
        self.assertNotIn("@codesetClause", sql)
        
        # Should have actual content with nested structure
        self.assertIn("m.measurement_date as start_date", sql)  # Inner query
        self.assertIn("JOIN @cdm_database_schema.PROVIDER PR", sql)  # PR alias
        self.assertIn("C.start_date", sql)  # Outer query WHERE clause
        self.assertIn("ROW_NUMBER() OVER", sql)  # first=True generates ordinal


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
            
            # All templates should have basic SQL structure (case-insensitive)
            self.assertIn("select", template.lower())
            self.assertIn("from", template.lower())
            self.assertIn("where", template.lower())
            
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


class TestDoseEraSqlBuilder(unittest.TestCase):
    """Test DoseEraSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = DoseEraSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@codesetClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@additionalColumns", template)
        self.assertIn("DOSE_ERA", template)
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = DoseEraSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        self.assertEqual(default_cols, expected_cols)
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = DoseEraSqlBuilder()
        
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT), "C.drug_concept_id")
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION), "DATEDIFF(d, C.start_date, C.end_date)")
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.UNIT), "C.unit_concept_id")
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.VALUE_AS_NUMBER), "C.dose_value")
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False, codeset_id=123)
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        self.assertNotIn("@codesetClause", result)
        self.assertIn("codeset_id = 123", result)
    
    def test_embed_codeset_clause_no_codeset(self):
        """Test codeset clause embedding with no codeset."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        self.assertNotIn("@codesetClause", result)
        self.assertEqual(result, "SELECT * FROM table ")
    
    def test_embed_ordinal_expression_first(self):
        """Test ordinal expression with first=True."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=True)
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertNotIn("@ordinalExpression", result)
        self.assertIn("row_number()", result)
        self.assertIn("C.ordinal = 1", where_clauses)
    
    def test_embed_ordinal_expression_not_first(self):
        """Test ordinal expression with first=False."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertNotIn("@ordinalExpression", result)
        self.assertNotIn("row_number()", result)
        self.assertEqual(len(where_clauses), 0)
    
    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        self.assertIn("de.person_id", select_clauses)
        self.assertIn("de.dose_era_id", select_clauses)
        self.assertIn("de.drug_concept_id", select_clauses)
        self.assertIn("de.unit_concept_id", select_clauses)
        self.assertIn("de.dose_value", select_clauses)
        self.assertIn("de.dose_era_start_date as start_date", " ".join(select_clauses))
        self.assertIn("de.dose_era_end_date as end_date", " ".join(select_clauses))
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 0)
    
    def test_resolve_join_clauses_with_person(self):
        """Test join clauses resolution with person join."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False, age_at_start=NumericRange(op=">=", value=18))
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 1)
        self.assertIn("PERSON P", join_clauses[0])
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(first=False)
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertEqual(len(where_clauses), 0)
    
    def test_resolve_where_clauses_with_filters(self):
        """Test where clauses resolution with filters."""
        builder = DoseEraSqlBuilder()
        criteria = DoseEra(
            first=False,
            era_start_date=DateRange(op=">=", value="2020-01-01"),
            dose_value=NumericRange(op=">", value=100)
        )
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertGreaterEqual(len(where_clauses), 2)
        self.assertTrue(any("C.start_date" in clause for clause in where_clauses))
        self.assertTrue(any("C.dose_value" in clause for clause in where_clauses))


class TestObservationPeriodSqlBuilder(unittest.TestCase):
    """Test ObservationPeriodSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = ObservationPeriodSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        # Note: ObservationPeriod doesn't use @codesetClause since it doesn't filter by concepts
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@additionalColumns", template)
        self.assertIn("OBSERVATION_PERIOD", template)
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = ObservationPeriodSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        self.assertEqual(default_cols, expected_cols)
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = ObservationPeriodSqlBuilder()
        
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT), "C.period_type_concept_id")
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION), "DATEDIFF(d, @startDateExpression, @endDateExpression)")
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        self.assertNotIn("@codesetClause", result)
        self.assertEqual(result, "SELECT * FROM table ")
    
    def test_embed_ordinal_expression(self):
        """Test ordinal expression embedding."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertNotIn("@ordinalExpression", result)
        self.assertEqual(len(where_clauses), 0)
    
    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        self.assertIn("op.person_id", select_clauses)
        self.assertIn("op.observation_period_id", select_clauses)
        self.assertIn("op.period_type_concept_id", select_clauses)
        self.assertIn("op.observation_period_start_date as start_date", " ".join(select_clauses))
        self.assertIn("op.observation_period_end_date as end_date", " ".join(select_clauses))
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 0)
    
    def test_resolve_join_clauses_with_person(self):
        """Test join clauses resolution with person join."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod(age_at_start=NumericRange(op=">=", value=18))
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 1)
        self.assertIn("PERSON P", join_clauses[0])
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod()
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertEqual(len(where_clauses), 0)
    
    def test_resolve_where_clauses_with_filters(self):
        """Test where clauses resolution with filters."""
        builder = ObservationPeriodSqlBuilder()
        criteria = ObservationPeriod(
            period_start_date=DateRange(op=">=", value="2020-01-01"),
            age_at_start=NumericRange(op=">", value=30)
        )
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertGreaterEqual(len(where_clauses), 1)
        self.assertTrue(any("C.start_date" in clause for clause in where_clauses))


class TestPayerPlanPeriodSqlBuilder(unittest.TestCase):
    """Test PayerPlanPeriodSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = PayerPlanPeriodSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@codesetClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@additionalColumns", template)
        self.assertIn("PAYER_PLAN_PERIOD", template)
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = PayerPlanPeriodSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        self.assertEqual(default_cols, expected_cols)
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = PayerPlanPeriodSqlBuilder()
        
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT), "C.payer_concept_id")
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        self.assertNotIn("@codesetClause", result)
        self.assertEqual(result, "SELECT * FROM table ")
    
    def test_embed_ordinal_expression(self):
        """Test ordinal expression embedding."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertNotIn("@ordinalExpression", result)
        self.assertEqual(len(where_clauses), 0)
    
    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        self.assertIn("ppp.person_id", select_clauses)
        self.assertIn("ppp.payer_plan_period_id", select_clauses)
        self.assertIn("ppp.payer_plan_period_start_date as start_date", " ".join(select_clauses))
        self.assertIn("ppp.payer_plan_period_end_date as end_date", " ".join(select_clauses))
    
    def test_resolve_select_clauses_with_concepts(self):
        """Test select clauses resolution with concept fields."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod(
            payer_source_concept=123,
            plan_source_concept=456,
            sponsor_source_concept=789
        )
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        self.assertIn("ppp.payer_source_concept_id", select_clauses)
        self.assertIn("ppp.plan_source_concept_id", select_clauses)
        self.assertIn("ppp.sponsor_source_concept_id", select_clauses)
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 0)
    
    def test_resolve_join_clauses_with_person(self):
        """Test join clauses resolution with person join."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod(age_at_start=NumericRange(op=">=", value=18))
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 1)
        self.assertIn("PERSON P", join_clauses[0])
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod()
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertEqual(len(where_clauses), 1)
        self.assertEqual(where_clauses[0], "1=1")
    
    def test_resolve_where_clauses_with_filters(self):
        """Test where clauses resolution with filters."""
        builder = PayerPlanPeriodSqlBuilder()
        criteria = PayerPlanPeriod(
            period_start_date=DateRange(op=">=", value="2020-01-01"),
            payer_source_concept=123
        )
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertGreaterEqual(len(where_clauses), 2)
        self.assertTrue(any("C.start_date" in clause for clause in where_clauses))
        self.assertTrue(any("payer_source_concept_id" in clause for clause in where_clauses))


class TestVisitDetailSqlBuilder(unittest.TestCase):
    """Test VisitDetailSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = VisitDetailSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@codesetClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@additionalColumns", template)
        self.assertIn("VISIT_DETAIL", template)
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = VisitDetailSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_DETAIL_ID}
        self.assertEqual(default_cols, expected_cols)
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = VisitDetailSqlBuilder()
        
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT), "C.visit_detail_concept_id")
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION), "DATEDIFF(d, C.start_date, C.end_date)")
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_DETAIL_ID), "C.visit_detail_id")
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False, codeset_id=123)
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        self.assertNotIn("@codesetClause", result)
        self.assertIn("Codesets", result)
    
    def test_embed_ordinal_expression_first(self):
        """Test ordinal expression with first=True."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False, first=True)
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertNotIn("@ordinalExpression", result)
        self.assertIn("row_number()", result)
        self.assertIn("C.ordinal = 1", where_clauses)
    
    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False)
        
        select_clauses = builder.resolve_select_clauses(criteria)
        
        self.assertIn("vd.person_id", select_clauses)
        self.assertIn("vd.visit_detail_id", select_clauses)
        self.assertIn("vd.visit_detail_concept_id", select_clauses)
        self.assertIn("vd.visit_occurrence_id", select_clauses)
        self.assertIn("vd.visit_detail_start_date as start_date", " ".join(select_clauses))
        self.assertIn("vd.visit_detail_end_date as end_date", " ".join(select_clauses))
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False)
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 0)
    
    def test_resolve_join_clauses_with_person(self):
        """Test join clauses resolution with person join."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False, age=NumericRange(op=">=", value=18))
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 1)
        self.assertIn("PERSON P", join_clauses[0])
    
    def test_resolve_join_clauses_with_care_site(self):
        """Test join clauses resolution with care site join."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(
            visit_detail_type_exclude=False, 
            place_of_service_cs=ConceptSetSelection(codeset_id=123, is_exclusion=False)
        )
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 1)
        self.assertIn("CARE_SITE CS", join_clauses[0])
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(visit_detail_type_exclude=False)
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertEqual(len(where_clauses), 0)
    
    def test_resolve_where_clauses_with_filters(self):
        """Test where clauses resolution with filters."""
        builder = VisitDetailSqlBuilder()
        criteria = VisitDetail(
            visit_detail_type_exclude=False,
            visit_detail_start_date=DateRange(op=">=", value="2020-01-01"),
            age=NumericRange(op=">", value=1)
        )
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertGreaterEqual(len(where_clauses), 2)
        self.assertTrue(any("C.start_date" in clause for clause in where_clauses))
        self.assertTrue(any("P.year_of_birth" in clause for clause in where_clauses))


class TestLocationRegionSqlBuilder(unittest.TestCase):
    """Test LocationRegionSqlBuilder class."""
    
    def test_get_query_template(self):
        """Test query template generation."""
        builder = LocationRegionSqlBuilder()
        template = builder.get_query_template()
        
        self.assertIn("@selectClause", template)
        self.assertIn("@codesetClause", template)
        self.assertIn("@joinClause", template)
        self.assertIn("@whereClause", template)
        self.assertIn("@ordinalExpression", template)
        self.assertIn("@additionalColumns", template)
        self.assertIn("LOCATION", template)
    
    def test_get_default_columns(self):
        """Test default columns."""
        builder = LocationRegionSqlBuilder()
        default_cols = builder.get_default_columns()
        
        expected_cols = {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID}
        self.assertEqual(default_cols, expected_cols)
    
    def test_get_table_column_for_criteria_column(self):
        """Test criteria column mapping."""
        builder = LocationRegionSqlBuilder()
        
        self.assertEqual(builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT), "C.region_concept_id")
    
    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        builder = LocationRegionSqlBuilder()
        criteria = LocationRegion()
        
        query = "SELECT * FROM table @codesetClause"
        result = builder.embed_codeset_clause(query, criteria)
        
        self.assertNotIn("@codesetClause", result)
        self.assertEqual(result, "SELECT * FROM table ")
    
    def test_embed_ordinal_expression(self):
        """Test ordinal expression embedding."""
        builder = LocationRegionSqlBuilder()
        criteria = LocationRegion()
        where_clauses = []
        
        query = "SELECT * FROM table @ordinalExpression"
        result = builder.embed_ordinal_expression(query, criteria, where_clauses)
        
        self.assertNotIn("@ordinalExpression", result)
        self.assertEqual(len(where_clauses), 0)
    
    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        builder = LocationRegionSqlBuilder()
        criteria = LocationRegion()
        
        join_clauses = builder.resolve_join_clauses(criteria)
        
        self.assertEqual(len(join_clauses), 0)
    
    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        builder = LocationRegionSqlBuilder()
        criteria = LocationRegion()
        
        where_clauses = builder.resolve_where_clauses(criteria)
        
        self.assertEqual(len(where_clauses), 0)


class TestBuilderIntegration(unittest.TestCase):
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
            self.assertTrue(hasattr(builder, 'get_query_template'))
            self.assertTrue(hasattr(builder, 'get_default_columns'))
            self.assertTrue(hasattr(builder, 'get_table_column_for_criteria_column'))
            self.assertTrue(hasattr(builder, 'embed_codeset_clause'))
            self.assertTrue(hasattr(builder, 'embed_ordinal_expression'))
            self.assertTrue(hasattr(builder, 'resolve_select_clauses'))
            self.assertTrue(hasattr(builder, 'resolve_join_clauses'))
            self.assertTrue(hasattr(builder, 'resolve_where_clauses'))
            
            # Test that methods are callable
            self.assertTrue(callable(builder.get_query_template))
            self.assertTrue(callable(builder.get_default_columns))
            self.assertTrue(callable(builder.get_table_column_for_criteria_column))
    
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
            self.assertIsInstance(builder.get_default_columns(), set)
            # Create mock criteria with required fields
            if builder.__class__.__name__ == "DoseEraSqlBuilder":
                mock_criteria = DoseEra(first=False)
            elif builder.__class__.__name__ == "VisitDetailSqlBuilder":
                mock_criteria = VisitDetail(visit_detail_type_exclude=False)
            else:
                mock_criteria = Mock()
            
            self.assertIsInstance(builder.resolve_select_clauses(mock_criteria, options), list)
            self.assertIsInstance(builder.resolve_join_clauses(mock_criteria, options), list)
            self.assertIsInstance(builder.resolve_where_clauses(mock_criteria, options), list)


if __name__ == '__main__':
    unittest.main()
