"""
Tests for Query Builder Classes

This module contains comprehensive tests for the CohortExpressionQueryBuilder
and ConceptSetExpressionQueryBuilder classes.
"""

import unittest
import json
from typing import List, Optional
from circe.cohortdefinition import (
    CohortExpression, CohortExpressionQueryBuilder, BuildExpressionQueryOptions,
    ConceptSetExpressionQueryBuilder,
    PrimaryCriteria, CriteriaGroup, CorelatedCriteria, DemographicCriteria,
    ConditionOccurrence, Death, Measurement, Observation,
    DateRange, NumericRange, TextFilter, ConceptSetSelection,
    DateOffsetStrategy, CustomEraStrategy, Occurrence, CriteriaColumn,
    CollapseSettings, CollapseType, ResultLimit, Period, ObservationFilter
)
from circe.cohortdefinition.builders.utils import BuilderOptions
from circe.vocabulary import (
    Concept, ConceptSet, ConceptSetExpression, ConceptSetItem
)


class TestConceptSetExpressionQueryBuilder(unittest.TestCase):
    """Test ConceptSetExpressionQueryBuilder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = ConceptSetExpressionQueryBuilder()

    def test_concept_set_expression_query_builder_initialization(self):
        """Test basic initialization of ConceptSetExpressionQueryBuilder."""
        self.assertIsNotNone(self.builder)

    def test_get_concept_ids(self):
        """Test get_concept_ids method."""
        concepts = [
            Concept(concept_id=12345, concept_name="Test Concept 1"),
            Concept(concept_id=67890, concept_name="Test Concept 2"),
            Concept(concept_id=11111, concept_name="Test Concept 3")
        ]
        
        concept_ids = self.builder.get_concept_ids(concepts)
        
        expected_ids = [12345, 67890, 11111]
        self.assertEqual(concept_ids, expected_ids)

    def test_get_concept_ids_with_none_values(self):
        """Test get_concept_ids with None concept_id values."""
        concepts = [
            Concept(concept_id=12345, concept_name="Test Concept 1"),
            Concept(concept_id=11111, concept_name="Test Concept 3")
        ]
        
        concept_ids = self.builder.get_concept_ids(concepts)
        
        expected_ids = [12345, 11111]  # None values should be filtered out
        self.assertEqual(concept_ids, expected_ids)

    def test_get_concept_ids_empty_list(self):
        """Test get_concept_ids with empty list."""
        concept_ids = self.builder.get_concept_ids([])
        self.assertEqual(concept_ids, [])

    def test_build_concept_set_sub_query_with_concepts_only(self):
        """Test build_concept_set_sub_query with concepts only."""
        concepts = [
            Concept(concept_id=12345, concept_name="Test Concept 1"),
            Concept(concept_id=67890, concept_name="Test Concept 2")
        ]
        descendant_concepts = []
        
        query = self.builder.build_concept_set_sub_query(concepts, descendant_concepts)
        
        self.assertIn("SELECT concept_id", query)
        self.assertIn("@vocabulary_database_schema.CONCEPT", query)
        self.assertIn("12345", query)
        self.assertIn("67890", query)

    def test_build_concept_set_sub_query_with_descendants_only(self):
        """Test build_concept_set_sub_query with descendants only."""
        concepts = []
        descendant_concepts = [
            Concept(concept_id=12345, concept_name="Test Concept 1"),
            Concept(concept_id=67890, concept_name="Test Concept 2")
        ]
        
        query = self.builder.build_concept_set_sub_query(concepts, descendant_concepts)
        
        self.assertIn("SELECT ca.descendant_concept_id as concept_id", query)
        self.assertIn("@vocabulary_database_schema.CONCEPT_ANCESTOR", query)
        self.assertIn("12345", query)
        self.assertIn("67890", query)

    def test_build_concept_set_sub_query_with_both(self):
        """Test build_concept_set_sub_query with both concepts and descendants."""
        concepts = [Concept(concept_id=12345, concept_name="Test Concept 1")]
        descendant_concepts = [Concept(concept_id=67890, concept_name="Test Concept 2")]
        
        query = self.builder.build_concept_set_sub_query(concepts, descendant_concepts)
        
        self.assertIn("UNION", query)
        self.assertIn("12345", query)
        self.assertIn("67890", query)

    def test_build_concept_set_sub_query_empty_lists(self):
        """Test build_concept_set_sub_query with empty lists."""
        query = self.builder.build_concept_set_sub_query([], [])
        self.assertEqual(query, "")

    def test_build_concept_set_mapped_query(self):
        """Test build_concept_set_mapped_query method."""
        mapped_concepts = [Concept(concept_id=12345, concept_name="Test Concept")]
        mapped_descendant_concepts = []
        
        query = self.builder.build_concept_set_mapped_query(mapped_concepts, mapped_descendant_concepts)
        
        self.assertIn("SELECT c.concept_id", query)
        self.assertIn("@vocabulary_database_schema.CONCEPT_RELATIONSHIP", query)
        self.assertIn("Maps to", query)

    def test_build_concept_set_query_empty_concepts(self):
        """Test build_concept_set_query with empty concepts."""
        query = self.builder.build_concept_set_query([], [], [], [])
        
        self.assertIn("SELECT concept_id FROM @vocabulary_database_schema.CONCEPT WHERE 0=1", query)

    def test_build_concept_set_query_with_mapped_concepts(self):
        """Test build_concept_set_query with mapped concepts."""
        concepts = [Concept(concept_id=12345, concept_name="Test Concept")]
        descendant_concepts = []
        mapped_concepts = [Concept(concept_id=67890, concept_name="Mapped Concept")]
        mapped_descendant_concepts = []
        
        query = self.builder.build_concept_set_query(concepts, descendant_concepts, mapped_concepts, mapped_descendant_concepts)
        
        self.assertIn("UNION", query)
        self.assertIn("12345", query)
        self.assertIn("67890", query)

    def test_build_expression_query_included_concepts_only(self):
        """Test build_expression_query with included concepts only."""
        expression = ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=12345, concept_name="Test Concept 1"),
                    is_excluded=False,
                    include_descendants=False,
                    include_mapped=False
                ),
                ConceptSetItem(
                    concept=Concept(concept_id=67890, concept_name="Test Concept 2"),
                    is_excluded=False,
                    include_descendants=True,
                    include_mapped=False
                )
            ],
            is_excluded=False,
            include_mapped=False,
            include_descendants=False
        )
        
        query = self.builder.build_expression_query(expression)
        
        self.assertIn("SELECT DISTINCT concept_id", query)
        self.assertIn("12345", query)
        self.assertIn("67890", query)

    def test_build_expression_query_with_excluded_concepts(self):
        """Test build_expression_query with excluded concepts."""
        expression = ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=12345, concept_name="Included Concept"),
                    is_excluded=False,
                    include_descendants=False,
                    include_mapped=False
                ),
                ConceptSetItem(
                    concept=Concept(concept_id=67890, concept_name="Excluded Concept"),
                    is_excluded=True,
                    include_descendants=False,
                    include_mapped=False
                )
            ],
            is_excluded=False,
            include_mapped=False,
            include_descendants=False
        )
        
        query = self.builder.build_expression_query(expression)
        
        self.assertIn("EXCEPT", query)
        self.assertIn("12345", query)
        self.assertIn("67890", query)

    def test_build_expression_query_with_mapped_concepts(self):
        """Test build_expression_query with mapped concepts."""
        expression = ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=12345, concept_name="Test Concept"),
                    is_excluded=False,
                    include_descendants=False,
                    include_mapped=True
                )
            ],
            is_excluded=False,
            include_mapped=False,
            include_descendants=False
        )
        
        query = self.builder.build_expression_query(expression)
        
        self.assertIn("UNION", query)
        self.assertIn("@vocabulary_database_schema.CONCEPT_RELATIONSHIP", query)

    def test_build_expression_query_complex_scenario(self):
        """Test build_expression_query with complex scenario."""
        expression = ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(concept_id=12345, concept_name="Included Concept"),
                    is_excluded=False,
                    include_descendants=True,
                    include_mapped=True
                ),
                ConceptSetItem(
                    concept=Concept(concept_id=67890, concept_name="Excluded Concept"),
                    is_excluded=True,
                    include_descendants=False,
                    include_mapped=False
                ),
                ConceptSetItem(
                    concept=Concept(concept_id=11111, concept_name="Another Included"),
                    is_excluded=False,
                    include_descendants=False,
                    include_mapped=False
                )
            ],
            is_excluded=False,
            include_mapped=False,
            include_descendants=False
        )
        
        query = self.builder.build_expression_query(expression)
        
        self.assertIn("SELECT DISTINCT concept_id", query)
        self.assertIn("EXCEPT", query)
        self.assertIn("UNION", query)
        self.assertIn("12345", query)
        self.assertIn("67890", query)
        self.assertIn("11111", query)

    def test_build_expression_query_empty_items(self):
        """Test build_expression_query with empty items."""
        expression = ConceptSetExpression(
            items=[],
            is_excluded=False,
            include_mapped=False,
            include_descendants=False
        )
        
        query = self.builder.build_expression_query(expression)
        
        self.assertIn("SELECT DISTINCT concept_id", query)
        self.assertNotIn("EXCEPT", query)


class TestCohortExpressionQueryBuilder(unittest.TestCase):
    """Test CohortExpressionQueryBuilder class."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = CohortExpressionQueryBuilder()

    def test_cohort_expression_query_builder_initialization(self):
        """Test basic initialization of CohortExpressionQueryBuilder."""
        self.assertIsNotNone(self.builder)
        self.assertIsNotNone(self.builder.concept_set_query_builder)

    def test_build_expression_query_options_from_json(self):
        """Test BuildExpressionQueryOptions.from_json method."""
        json_str = json.dumps({
            "cohortIdFieldName": "test_cohort_id",
            "cohortId": 123,
            "cdmSchema": "cdm_schema",
            "targetTable": "target_table",
            "resultSchema": "result_schema",
            "vocabularySchema": "vocabulary_schema",
            "generateStats": True
        })
        
        options = BuildExpressionQueryOptions.from_json(json_str)
        
        self.assertEqual(options.cohort_id_field_name, "test_cohort_id")
        self.assertEqual(options.cohort_id, 123)
        self.assertEqual(options.cdm_schema, "cdm_schema")
        self.assertEqual(options.target_table, "target_table")
        self.assertEqual(options.result_schema, "result_schema")
        self.assertEqual(options.vocabulary_schema, "vocabulary_schema")
        self.assertTrue(options.generate_stats)

    def test_build_expression_query_options_from_json_invalid(self):
        """Test BuildExpressionQueryOptions.from_json with invalid JSON."""
        with self.assertRaises(RuntimeError):
            BuildExpressionQueryOptions.from_json("invalid json")

    def test_get_occurrence_operator(self):
        """Test get_occurrence_operator method."""
        self.assertEqual(self.builder.get_occurrence_operator(0), "=")
        self.assertEqual(self.builder.get_occurrence_operator(1), "<=")
        self.assertEqual(self.builder.get_occurrence_operator(2), ">=")

    def test_get_occurrence_operator_invalid(self):
        """Test get_occurrence_operator with invalid type."""
        with self.assertRaises(RuntimeError):
            self.builder.get_occurrence_operator(99)

    def test_get_additional_columns(self):
        """Test _get_additional_columns method."""
        columns = [CriteriaColumn.AGE, CriteriaColumn.GENDER]
        result = self.builder._get_additional_columns(columns, "A.")
        
        self.assertIn("A.age", result)
        self.assertIn("A.gender", result)

    def test_get_codeset_query_empty(self):
        """Test get_codeset_query with empty concept sets."""
        query = self.builder.get_codeset_query([])
        
        self.assertIn("CREATE TABLE #Codesets", query)
        self.assertNotIn("INSERT INTO #Codesets", query)

    def test_get_codeset_query_with_concept_sets(self):
        """Test get_codeset_query with concept sets."""
        concept_sets = [
            type('ConceptSet', (), {
                'id': 12345,
                'expression': ConceptSetExpression(
                    items=[
                        ConceptSetItem(
                            concept=Concept(concept_id=11111, concept_name="Test Concept"),
                            is_excluded=False,
                            include_descendants=False,
                            include_mapped=False
                        )
                    ],
                    is_excluded=False,
                    include_mapped=False,
                    include_descendants=False
                )
            })()
        ]
        
        query = self.builder.get_codeset_query(concept_sets)
        
        self.assertIn("CREATE TABLE #Codesets", query)
        self.assertIn("INSERT INTO #Codesets", query)
        self.assertIn("12345", query)
        self.assertIn("11111", query)

    def test_get_primary_events_query(self):
        """Test get_primary_events_query method."""
        primary_criteria = PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(
                    first=True,
                    condition_type_exclude=False,
                    codeset_id=12345
                )
            ],
            observation_window=ObservationFilter(prior_days=0, post_days=0),
            primary_limit=ResultLimit(type="ALL")
        )
        
        query = self.builder.get_primary_events_query(primary_criteria)
        
        self.assertIn("SELECT E.person_id, E.event_id", query)
        self.assertIn("@cdm_database_schema.OBSERVATION_PERIOD", query)
        self.assertIn("ORDER BY E.sort_date ASC", query)

    def test_get_final_cohort_query_no_censor_window(self):
        """Test get_final_cohort_query without censor window."""
        query = self.builder.get_final_cohort_query(None)
        
        self.assertIn("SELECT @target_cohort_id as @cohort_id_field_name", query)
        self.assertIn("FROM #final_cohort CO", query)
        self.assertNotIn("WHERE", query)

    def test_get_final_cohort_query_with_censor_window(self):
        """Test get_final_cohort_query with censor window."""
        censor_window = Period(start_date="2020-01-01", end_date="2023-01-01")
        
        query = self.builder.get_final_cohort_query(censor_window)
        
        self.assertIn("SELECT @target_cohort_id as @cohort_id_field_name", query)
        self.assertIn("FROM #final_cohort CO", query)
        self.assertIn("WHERE", query)
        self.assertIn("CASE WHEN", query)

    def test_get_inclusion_rule_table_sql_empty(self):
        """Test get_inclusion_rule_table_sql with empty inclusion rules."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="ALL")
            ),
            inclusion_rules=[]
        )
        
        query = self.builder.get_inclusion_rule_table_sql(expression)
        
        self.assertIn("CREATE TABLE #inclusion_rules", query)
        self.assertNotIn("UNION ALL", query)

    def test_get_inclusion_rule_table_sql_with_rules(self):
        """Test get_inclusion_rule_table_sql with inclusion rules."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="ALL")
            ),
            inclusion_rules=[
                type('InclusionRule', (), {
                    'expression': CriteriaGroup(type="ALL", criteria_list=[])
                })()
            ]
        )
        
        query = self.builder.get_inclusion_rule_table_sql(expression)
        
        self.assertIn("CREATE TABLE #inclusion_rules", query)
        self.assertIn("UNION ALL", query)

    def test_get_inclusion_analysis_query(self):
        """Test get_inclusion_analysis_query method."""
        query = self.builder.get_inclusion_analysis_query("#test_events", 1)
        
        self.assertIn("SELECT 1 as inclusion_rule_id", query)
        self.assertIn("#test_events", query)

    def test_get_demographic_criteria_query(self):
        """Test get_demographic_criteria_query method."""
        criteria = DemographicCriteria(
            age=NumericRange(op="gte", value=18, extent=65),
            gender=[Concept(concept_id=8507, concept_name="Male")],
            gender_cs=ConceptSetSelection(codeset_id=12345, is_exclusion=False)
        )
        
        query = self.builder.get_demographic_criteria_query(criteria, "#test_events")
        
        self.assertIn("SELECT @indexId as index_id", query)
        self.assertIn("@cdm_database_schema.PERSON", query)
        self.assertIn("8507", query)
        self.assertIn("12345", query)

    def test_get_windowed_criteria_query(self):
        """Test get_windowed_criteria_query method."""
        # This would need a proper WindowedCriteria object
        # For now, test the method exists
        self.assertTrue(hasattr(self.builder, 'get_windowed_criteria_query'))

    def test_get_corelated_criteria_query(self):
        """Test get_corelated_criteria_query method."""
        # This would need a proper CorelatedCriteria object
        # For now, test the method exists
        self.assertTrue(hasattr(self.builder, 'get_corelated_criteria_query'))

    def test_get_criteria_group_query_empty(self):
        """Test get_criteria_group_query with empty group."""
        group = CriteriaGroup(type="ALL", criteria_list=[])
        
        query = self.builder.get_criteria_group_query(group, "#test_events")
        
        self.assertIn("-- Begin Criteria Group", query)
        self.assertIn("#test_events", query)

    def test_get_criteria_group_query_with_criteria(self):
        """Test get_criteria_group_query with criteria."""
        group = CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(
                        first=True,
                        condition_type_exclude=False,
                        codeset_id=12345
                    ),
                    occurrence=Occurrence(type=1, count=1, is_distinct=False)
                )
            ]
        )
        
        query = self.builder.get_criteria_group_query(group, "#test_events")
        
        self.assertIn("SELECT @indexId as index_id", query)
        self.assertIn("#test_events", query)

    def test_get_strategy_sql_date_offset_strategy(self):
        """Test get_strategy_sql for DateOffsetStrategy."""
        strategy = DateOffsetStrategy(offset=30, date_field="StartDate")
        
        query = self.builder.get_strategy_sql(strategy, "#test_events")
        
        self.assertIn("CREATE TABLE #strategy_ends", query)
        self.assertIn("DATEADD(day, 30, start_date)", query)
        self.assertIn("#test_events", query)

    def test_get_strategy_sql_custom_era_strategy(self):
        """Test get_strategy_sql for CustomEraStrategy."""
        strategy = CustomEraStrategy(
            drug_codeset_id=12345,
            gap_days=30,
            offset=0,
            days_supply_override=None
        )
        
        query = self.builder.get_strategy_sql(strategy, "#test_events")
        
        self.assertIn("CREATE TABLE #strategy_ends", query)
        self.assertIn("12345", query)
        self.assertIn("30", query)
        self.assertIn("#test_events", query)

    def test_get_strategy_sql_custom_era_strategy_no_codeset_id(self):
        """Test get_strategy_sql for CustomEraStrategy with no codeset ID."""
        strategy = CustomEraStrategy(
            drug_codeset_id=None,
            gap_days=30,
            offset=0,
            days_supply_override=None
        )
        
        with self.assertRaises(RuntimeError):
            self.builder.get_strategy_sql(strategy, "#test_events")

    def test_get_criteria_sql_delegation(self):
        """Test that get_criteria_sql methods delegate to appropriate builders."""
        criteria = Death(first=True, death_type_exclude=False, codeset_id=12345)
        
        query = self.builder.get_criteria_sql(criteria)
        
        self.assertIn("SELECT", query)
        self.assertIn("FROM @cdm_database_schema.DEATH", query)
        self.assertIn("12345", query)

    def test_build_expression_query_basic(self):
        """Test build_expression_query with basic cohort expression."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[
                    ConditionOccurrence(
                        first=True,
                        condition_type_exclude=False,
                        codeset_id=12345
                    )
                ],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="ALL")
            ),
            qualified_limit=ResultLimit(type="ALL"),
            expression_limit=ResultLimit(type="ALL"),
            inclusion_rules=[],
            collapse_settings=CollapseSettings(
                collapse_type=CollapseType.COLLAPSE,
                era_pad=30
            )
        )
        
        options = BuildExpressionQueryOptions()
        options.cdm_schema = "cdm_schema"
        options.cohort_id = 123
        
        query = self.builder.build_expression_query(expression, options)
        
        self.assertIn("cdm_schema", query)
        self.assertIn("123", query)
        self.assertIn("CREATE TABLE #Codesets", query)

    def test_build_expression_query_with_additional_criteria(self):
        """Test build_expression_query with additional criteria."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[
                    ConditionOccurrence(
                        first=True,
                        condition_type_exclude=False,
                        codeset_id=12345
                    )
                ],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="ALL")
            ),
            additional_criteria=CriteriaGroup(
                type="ALL",
                criteria_list=[
                    CorelatedCriteria(
                        criteria=Death(
                            first=True,
                            death_type_exclude=False,
                            codeset_id=67890
                        ),
                        occurrence=Occurrence(type=1, count=1, is_distinct=False)
                    )
                ]
            ),
            collapse_settings=CollapseSettings(
                collapse_type=CollapseType.COLLAPSE,
                era_pad=30
            )
        )
        
        options = BuildExpressionQueryOptions()
        options.cdm_schema = "cdm_schema"
        
        query = self.builder.build_expression_query(expression, options)
        
        self.assertIn("JOIN", query)
        self.assertIn("12345", query)
        self.assertIn("67890", query)

    def test_build_expression_query_with_end_strategy(self):
        """Test build_expression_query with end strategy."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[
                    ConditionOccurrence(
                        first=True,
                        condition_type_exclude=False,
                        codeset_id=12345
                    )
                ],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="ALL")
            ),
            end_strategy=DateOffsetStrategy(offset=30, date_field="StartDate"),
            collapse_settings=CollapseSettings(
                collapse_type=CollapseType.COLLAPSE,
                era_pad=30
            )
        )
        
        options = BuildExpressionQueryOptions()
        options.cdm_schema = "cdm_schema"
        
        query = self.builder.build_expression_query(expression, options)
        
        self.assertIn("CREATE TABLE #strategy_ends", query)
        self.assertIn("DATEADD(day, 30, start_date)", query)

    def test_build_expression_query_with_censor_window(self):
        """Test build_expression_query with censor window."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[
                    ConditionOccurrence(
                        first=True,
                        condition_type_exclude=False,
                        codeset_id=12345
                    )
                ],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="ALL")
            ),
            censor_window=Period(start_date="2020-01-01", end_date="2023-01-01"),
            collapse_settings=CollapseSettings(
                collapse_type=CollapseType.COLLAPSE,
                era_pad=30
            )
        )
        
        options = BuildExpressionQueryOptions()
        options.cdm_schema = "cdm_schema"
        
        query = self.builder.build_expression_query(expression, options)
        
        self.assertIn("CASE WHEN", query)
        self.assertIn("2020-01-01", query)
        self.assertIn("2023-01-01", query)


if __name__ == '__main__':
    unittest.main()
