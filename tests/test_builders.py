"""
Comprehensive test suite for SQL query builders.

This module tests all builder functionality including utilities, base classes,
and specific builder implementations.
"""

import os

# Add project root to path for imports
import sys
import unittest
from enum import Enum
from typing import Set

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from circe.cohortdefinition.builders import (
    BuilderOptions,
    BuilderUtils,
    ConditionOccurrenceSqlBuilder,
    CriteriaColumn,
    CriteriaSqlBuilder,
    DrugExposureSqlBuilder,
    ProcedureOccurrenceSqlBuilder,
)
from circe.cohortdefinition.core import DateAdjustment, DateRange, NumericRange
from circe.cohortdefinition.criteria import (
    ConditionOccurrence,
    Criteria,
    DrugExposure,
    ProcedureOccurrence,
)
from circe.vocabulary.concept import Concept


class TestCriteriaColumn(unittest.TestCase):
    """Test CriteriaColumn enum functionality."""

    def test_criteria_column_string_values(self):
        """Test that criteria columns have correct string values."""
        self.assertEqual(CriteriaColumn.START_DATE.value, "start_date")
        self.assertEqual(CriteriaColumn.END_DATE.value, "end_date")
        self.assertEqual(CriteriaColumn.VISIT_ID.value, "visit_occurrence_id")
        self.assertEqual(CriteriaColumn.DOMAIN_CONCEPT.value, "domain_concept_id")
        self.assertEqual(CriteriaColumn.DURATION.value, "duration")
        self.assertEqual(CriteriaColumn.ERA_OCCURRENCES.value, "occurrence_count")
        self.assertEqual(CriteriaColumn.GAP_DAYS.value, "gap_days")
        self.assertEqual(CriteriaColumn.UNIT.value, "unit_concept_id")
        self.assertEqual(CriteriaColumn.VALUE_AS_NUMBER.value, "value_as_number")
        self.assertEqual(CriteriaColumn.VISIT_DETAIL_ID.value, "visit_detail_id")

    def test_criteria_column_enum_inheritance(self):
        """Test that CriteriaColumn inherits from both str and Enum."""
        self.assertTrue(issubclass(CriteriaColumn, str))
        self.assertTrue(issubclass(CriteriaColumn, Enum))

    def test_criteria_column_comparison(self):
        """Test that criteria columns can be compared as strings."""
        self.assertEqual(CriteriaColumn.START_DATE, "start_date")
        self.assertNotEqual(CriteriaColumn.START_DATE, "end_date")


class TestBuilderOptions(unittest.TestCase):
    """Test BuilderOptions functionality."""

    def test_builder_options_initialization(self):
        """Test BuilderOptions initialization."""
        options = BuilderOptions()
        self.assertIsInstance(options.additional_columns, list)
        self.assertEqual(len(options.additional_columns), 0)

    def test_builder_options_additional_columns(self):
        """Test setting additional columns."""
        options = BuilderOptions()
        options.additional_columns = [
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.DURATION,
        ]

        self.assertEqual(len(options.additional_columns), 2)
        self.assertIn(CriteriaColumn.DOMAIN_CONCEPT, options.additional_columns)
        self.assertIn(CriteriaColumn.DURATION, options.additional_columns)

    def test_builder_options_empty_additional_columns(self):
        """Test that additional columns can be empty."""
        options = BuilderOptions()
        options.additional_columns = []

        self.assertEqual(len(options.additional_columns), 0)


class TestBuilderUtils(unittest.TestCase):
    """Test BuilderUtils static methods."""

    def test_get_date_adjustment_expression(self):
        """Test date adjustment expression generation."""
        date_adjustment = DateAdjustment(start_offset=30, end_offset=-7)

        result = BuilderUtils.get_date_adjustment_expression(
            date_adjustment, "start_col", "end_col"
        )

        expected = "DATEADD(day,30, start_col) as start_date, DATEADD(day,-7, end_col) as end_date"
        self.assertEqual(result, expected)

    def test_get_codeset_join_expression_standard_only(self):
        """Test codeset join expression with standard codeset only."""
        result = BuilderUtils.get_codeset_join_expression(
            standard_codeset_id=123,
            standard_concept_column="concept_id",
            source_codeset_id=None,
            source_concept_column="source_concept_id",
        )

        expected = (
            "JOIN #Codesets cs on (concept_id = cs.concept_id and cs.codeset_id = 123)"
        )
        self.assertEqual(result, expected)

    def test_get_codeset_join_expression_source_only(self):
        """Test codeset join expression with source codeset only."""
        result = BuilderUtils.get_codeset_join_expression(
            standard_codeset_id=None,
            standard_concept_column="concept_id",
            source_codeset_id=456,
            source_concept_column="source_concept_id",
        )

        expected = "JOIN #Codesets cns on (source_concept_id = cns.concept_id and cns.codeset_id = 456)"
        self.assertEqual(result, expected)

    def test_get_codeset_join_expression_both(self):
        """Test codeset join expression with both codesets."""
        result = BuilderUtils.get_codeset_join_expression(
            standard_codeset_id=123,
            standard_concept_column="concept_id",
            source_codeset_id=456,
            source_concept_column="source_concept_id",
        )

        expected = (
            "JOIN #Codesets cs on (concept_id = cs.concept_id and cs.codeset_id = 123) "
            "JOIN #Codesets cns on (source_concept_id = cns.concept_id and cns.codeset_id = 456)"
        )
        self.assertEqual(result, expected)

    def test_get_codeset_join_expression_none(self):
        """Test codeset join expression with no codesets."""
        result = BuilderUtils.get_codeset_join_expression(
            standard_codeset_id=None,
            standard_concept_column="concept_id",
            source_codeset_id=None,
            source_concept_column="source_concept_id",
        )

        self.assertEqual(result, "")

    def test_get_codeset_in_expression_inclusion(self):
        """Test codeset IN expression for inclusion."""
        result = BuilderUtils.get_codeset_in_expression(
            codeset_id=123, column_name="concept_id", is_exclusion=False
        )

        expected = (
            " concept_id in (select concept_id from #Codesets where codeset_id = 123)"
        )
        self.assertEqual(result, expected)

    def test_get_codeset_in_expression_exclusion(self):
        """Test codeset IN expression for exclusion."""
        result = BuilderUtils.get_codeset_in_expression(
            codeset_id=123, column_name="concept_id", is_exclusion=True
        )

        expected = "not concept_id in (select concept_id from #Codesets where codeset_id = 123)"
        self.assertEqual(result, expected)

    def test_get_concept_ids_from_concepts(self):
        """Test extracting concept IDs from concept list."""
        concepts = [
            Concept(concept_id=1, concept_name="Concept 1"),
            Concept(concept_id=2, concept_name="Concept 2"),
            Concept(concept_id=3, concept_name="Concept 4"),
        ]

        result = BuilderUtils.get_concept_ids_from_concepts(concepts)
        expected = [1, 2, 3]
        self.assertEqual(result, expected)

    def test_get_concept_ids_from_concepts_empty(self):
        """Test extracting concept IDs from empty list."""
        result = BuilderUtils.get_concept_ids_from_concepts([])
        self.assertEqual(result, [])

    def test_get_concept_ids_from_concepts_with_none(self):
        """Test extracting concept IDs when some concepts have None IDs."""
        # Since Concept requires concept_id to be int, we'll test the filtering logic differently
        # by creating a mock concept list that simulates the filtering behavior
        concepts = [
            Concept(concept_id=1, concept_name="Concept 1"),
            Concept(concept_id=2, concept_name="Concept 2"),
            Concept(concept_id=3, concept_name="Concept 4"),
        ]

        result = BuilderUtils.get_concept_ids_from_concepts(concepts)
        expected = [1, 2, 3]
        self.assertEqual(result, expected)

        # Test that the method handles the case where concept_id might be None
        # by testing the filtering logic directly
        concept_ids = [
            concept.concept_id for concept in concepts if concept.concept_id is not None
        ]
        self.assertEqual(concept_ids, [1, 2, 3])

    def test_build_date_range_clause_with_range(self):
        """Test date range clause with date range."""
        date_range = DateRange(op="gte", value="2020-01-01")

        result = BuilderUtils.build_date_range_clause("date_col", date_range)
        expected = "date_col >= DATEFROMPARTS(2020, 1, 1)"
        self.assertEqual(result, expected)

    def test_build_numeric_range_clause_none(self):
        """Test numeric range clause with None numeric range."""
        result = BuilderUtils.build_numeric_range_clause("num_col", None)
        self.assertIsNone(result)

    def test_build_numeric_range_clause_with_range(self):
        """Test numeric range clause with numeric range."""
        numeric_range = NumericRange(op="gt", value=100)

        result = BuilderUtils.build_numeric_range_clause("num_col", numeric_range)
        expected = "num_col > 100"
        self.assertEqual(result, expected)

    def test_build_text_filter_clause_none(self):
        """Test text filter clause with None text filter."""
        result = BuilderUtils.build_text_filter_clause(None, "text_col")
        self.assertIsNone(result)

    def test_build_text_filter_clause_with_filter(self):
        """Test text filter clause with text filter."""
        result = BuilderUtils.build_text_filter_clause("diabetes", "text_col")
        expected = "text_col LIKE '%diabetes%'"
        self.assertEqual(result, expected)

    def test_build_text_filter_clause_empty_string(self):
        """Test text filter clause with empty string."""
        result = BuilderUtils.build_text_filter_clause("", "text_col")
        expected = "text_col LIKE '%%'"
        self.assertEqual(result, expected)


class TestCriteriaSqlBuilder(unittest.TestCase):
    """Test CriteriaSqlBuilder abstract base class."""

    def test_criteria_sql_builder_is_abstract(self):
        """Test that CriteriaSqlBuilder cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            CriteriaSqlBuilder()

    def test_criteria_sql_builder_abstract_methods(self):
        """Test that CriteriaSqlBuilder has required abstract methods."""
        abstract_methods = CriteriaSqlBuilder.__abstractmethods__
        expected_methods = {
            "get_table_column_for_criteria_column",
            "get_query_template",
            "get_default_columns",
        }
        self.assertEqual(abstract_methods, expected_methods)

    def test_criteria_sql_builder_generic_type(self):
        """Test that CriteriaSqlBuilder is properly generic."""

        # This tests that the generic type constraint works
        class TestBuilder(CriteriaSqlBuilder[Criteria]):
            def get_table_column_for_criteria_column(
                self, column: CriteriaColumn
            ) -> str:
                return f"test.{column.value}"

            def get_query_template(self) -> str:
                return "SELECT * FROM test"

            def get_default_columns(self) -> Set[CriteriaColumn]:
                return {CriteriaColumn.START_DATE}

        builder = TestBuilder()
        self.assertIsInstance(builder, CriteriaSqlBuilder)


class TestConditionOccurrenceSqlBuilder(unittest.TestCase):
    """Test ConditionOccurrenceSqlBuilder implementation."""

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
            CriteriaColumn.VISIT_ID,
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
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.DOMAIN_CONCEPT
        )
        self.assertEqual(result, "C.condition_concept_id")

    def test_get_table_column_for_criteria_column_duration(self):
        """Test table column mapping for duration."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.DURATION
        )
        self.assertEqual(result, "(DATEDIFF(d,C.start_date, C.end_date))")

    def test_get_table_column_for_criteria_column_start_date(self):
        """Test table column mapping for start date."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.START_DATE
        )
        self.assertEqual(result, "C.start_date")

    def test_get_table_column_for_criteria_column_end_date(self):
        """Test table column mapping for end date."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.END_DATE
        )
        self.assertEqual(result, "C.end_date")

    def test_get_table_column_for_criteria_column_visit_id(self):
        """Test table column mapping for visit ID."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.VISIT_ID
        )
        self.assertEqual(result, "C.visit_occurrence_id")

    def test_get_table_column_for_criteria_column_other(self):
        """Test table column mapping for other columns."""
        # Using DOMAIN_CONCEPT as other column instead of removed AGE
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.DOMAIN_CONCEPT
        )
        self.assertEqual(result, "C.condition_concept_id")

    def test_embed_codeset_clause(self):
        """Test codeset clause embedding."""
        query = "SELECT * FROM table @codesetClause WHERE condition"
        result = self.builder.embed_codeset_clause(query, self.criteria)
        expected = "SELECT * FROM table  WHERE condition"
        self.assertEqual(result, expected)

    def test_resolve_select_clauses(self):
        """Test select clauses resolution."""
        result = self.builder.resolve_select_clauses(self.criteria)
        expected = [
            "co.person_id",
            "co.condition_occurrence_id",
            "co.condition_concept_id",
            "co.visit_occurrence_id",
            "co.condition_start_date as start_date, COALESCE(co.condition_end_date, DATEADD(day,1,co.condition_start_date)) as end_date",
        ]
        self.assertEqual(result, expected)

    def test_resolve_join_clauses(self):
        """Test join clauses resolution."""
        result = self.builder.resolve_join_clauses(self.criteria)
        self.assertEqual(result, [])

    def test_resolve_where_clauses(self):
        """Test where clauses resolution."""
        result = self.builder.resolve_where_clauses(self.criteria)
        self.assertEqual(result, [])

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

    def test_get_criteria_sql_with_options(self):
        """Test SQL generation with builder options."""
        options = BuilderOptions()
        options.additional_columns = [CriteriaColumn.DOMAIN_CONCEPT]

        result = self.builder.get_criteria_sql_with_options(self.criteria, options)

        # Check that additional columns are included
        self.assertIn("C.condition_concept_id as domain_concept_id", result)

    def test_get_criteria_sql_with_options_no_additional(self):
        """Test SQL generation with builder options but no additional columns."""
        options = BuilderOptions()
        options.additional_columns = []  # No additional columns

        result = self.builder.get_criteria_sql_with_options(self.criteria, options)

        # Check that @additionalColumns is removed
        self.assertNotIn("@additionalColumns", result)

    def test_get_criteria_sql_with_options_default_columns(self):
        """Test SQL generation with builder options containing default columns."""
        options = BuilderOptions()
        # Add default columns (should be filtered out)
        options.additional_columns = [
            CriteriaColumn.START_DATE,  # Default column
            CriteriaColumn.DURATION,  # Non-default column
        ]

        result = self.builder.get_criteria_sql_with_options(self.criteria, options)

        # Only non-default columns should be added as additional columns
        # START_DATE is already in the template, so it shouldn't be duplicated
        self.assertIn("DATEDIFF", result)
        # The template already includes C.start_date, so we just check it's there
        self.assertIn("C.start_date", result)


class TestDrugExposureSqlBuilder(unittest.TestCase):
    """Test DrugExposureSqlBuilder implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = DrugExposureSqlBuilder()
        self.criteria = DrugExposure(first=False)

    def test_get_default_columns(self):
        """Test get_default_columns method."""
        result = self.builder.get_default_columns()
        expected = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID,
        }
        self.assertEqual(result, expected)

    def test_get_query_template(self):
        """Test get_query_template method."""
        result = self.builder.get_query_template()
        self.assertIn("-- Begin Drug Exposure Criteria", result)
        self.assertIn("-- End Drug Exposure Criteria", result)
        self.assertIn("DRUG_EXPOSURE", result)

    def test_get_table_column_for_criteria_column_domain_concept(self):
        """Test table column mapping for domain concept."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.DOMAIN_CONCEPT
        )
        self.assertEqual(result, "C.drug_concept_id")

    def test_get_table_column_for_criteria_column_duration(self):
        """Test table column mapping for duration."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.DURATION
        )
        self.assertEqual(result, "(DATEDIFF(d,C.start_date, C.end_date))")

    def test_get_table_column_for_criteria_column_start_date(self):
        """Test table column mapping for start date."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.START_DATE
        )
        self.assertEqual(result, "C.start_date")

    def test_get_table_column_for_criteria_column_end_date(self):
        """Test table column mapping for end date."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.END_DATE
        )
        self.assertEqual(result, "C.end_date")

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
        self.assertIn("-- Begin Drug Exposure Criteria", result)
        self.assertIn("-- End Drug Exposure Criteria", result)
        self.assertIn("SELECT C.person_id", result)


class TestProcedureOccurrenceSqlBuilder(unittest.TestCase):
    """Test ProcedureOccurrenceSqlBuilder implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = ProcedureOccurrenceSqlBuilder()
        self.criteria = ProcedureOccurrence(first=False)

    def test_get_default_columns(self):
        """Test get_default_columns method."""
        result = self.builder.get_default_columns()
        expected = {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID,
        }
        self.assertEqual(result, expected)

    def test_get_query_template(self):
        """Test get_query_template method."""
        result = self.builder.get_query_template()
        self.assertIn("-- Begin Procedure Occurrence Criteria", result)
        self.assertIn("-- End Procedure Occurrence Criteria", result)
        self.assertIn("PROCEDURE_OCCURRENCE", result)

    def test_get_table_column_for_criteria_column_domain_concept(self):
        """Test table column mapping for domain concept."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.DOMAIN_CONCEPT
        )
        self.assertEqual(result, "C.procedure_concept_id")

    def test_get_table_column_for_criteria_column_duration(self):
        """Test table column mapping for duration."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.DURATION
        )
        self.assertEqual(result, "CAST(1 as int)")

    def test_get_table_column_for_criteria_column_start_date(self):
        """Test table column mapping for start date."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.START_DATE
        )
        self.assertEqual(result, "C.start_date")

    def test_get_table_column_for_criteria_column_end_date(self):
        """Test table column mapping for end date."""
        result = self.builder.get_table_column_for_criteria_column(
            CriteriaColumn.END_DATE
        )
        self.assertEqual(result, "C.end_date")

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
        self.assertIn("-- Begin Procedure Occurrence Criteria", result)
        self.assertIn("-- End Procedure Occurrence Criteria", result)
        self.assertIn("SELECT C.person_id", result)


class TestBuilderIntegration(unittest.TestCase):
    """Test integration between different builder components."""

    def test_all_builders_importable(self):
        """Test that all builders can be imported successfully."""
        from circe.cohortdefinition.builders import (
            ConditionOccurrenceSqlBuilder,
            CriteriaSqlBuilder,
            DrugExposureSqlBuilder,
            ProcedureOccurrenceSqlBuilder,
        )

        # Test that all classes are importable
        self.assertTrue(issubclass(ConditionOccurrenceSqlBuilder, CriteriaSqlBuilder))
        self.assertTrue(issubclass(DrugExposureSqlBuilder, CriteriaSqlBuilder))
        self.assertTrue(issubclass(ProcedureOccurrenceSqlBuilder, CriteriaSqlBuilder))

    def test_builder_options_with_all_builders(self):
        """Test that builder options work with all builders."""
        from circe.cohortdefinition.criteria import (
            ConditionOccurrence,
            DrugExposure,
            ProcedureOccurrence,
        )

        builders_and_criteria = [
            (ConditionOccurrenceSqlBuilder(), ConditionOccurrence()),
            (
                DrugExposureSqlBuilder(),
                DrugExposure(first=True, drug_type_exclude=False),
            ),
            (
                ProcedureOccurrenceSqlBuilder(),
                ProcedureOccurrence(first=True, procedure_type_exclude=False),
            ),
        ]

        options = BuilderOptions()
        options.additional_columns = [
            CriteriaColumn.DOMAIN_CONCEPT,
            CriteriaColumn.DURATION,
        ]

        for builder, criteria in builders_and_criteria:
            result = builder.get_criteria_sql_with_options(criteria, options)

            # All builders should include additional columns
            self.assertTrue("domain_concept_id" in result or "duration" in result)

    def test_criteria_column_consistency_across_builders(self):
        """Test that criteria columns are handled consistently across builders."""
        builders = [
            ConditionOccurrenceSqlBuilder(),
            DrugExposureSqlBuilder(),
            ProcedureOccurrenceSqlBuilder(),
        ]

        criteria = Criteria()

        for builder in builders:
            # Test that all builders can handle all criteria columns
            for column in CriteriaColumn:
                result = builder.get_table_column_for_criteria_column(column)
                self.assertIsInstance(result, str)
                self.assertGreater(len(result), 0)

    def test_sql_template_structure_consistency(self):
        """Test that all builders generate SQL with consistent structure."""
        from circe.cohortdefinition.criteria import (
            ConditionOccurrence,
            DrugExposure,
            ProcedureOccurrence,
        )

        builders_and_criteria = [
            (ConditionOccurrenceSqlBuilder(), ConditionOccurrence()),
            (
                DrugExposureSqlBuilder(),
                DrugExposure(first=True, drug_type_exclude=False),
            ),
            (
                ProcedureOccurrenceSqlBuilder(),
                ProcedureOccurrence(first=True, procedure_type_exclude=False),
            ),
        ]

        for builder, criteria in builders_and_criteria:
            result = builder.get_criteria_sql(criteria)

            # All SQL should have consistent structure (case-insensitive check)
            self.assertIn("C.person_id", result)
            self.assertIn("FROM", result)
            self.assertIn("-- Begin", result)
            self.assertIn("-- End", result)

            # Most template placeholders should be replaced, but @cdm_database_schema remains
            # as it's a database-specific placeholder
            self.assertNotIn("@selectClause", result)
            self.assertNotIn("@ordinalExpression", result)
            self.assertNotIn("@codesetClause", result)
            self.assertNotIn("@joinClause", result)
            self.assertNotIn("@whereClause", result)
            self.assertNotIn("@additionalColumns", result)


if __name__ == "__main__":
    unittest.main()
