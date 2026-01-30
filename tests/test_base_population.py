
import unittest
from circe.cohortdefinition.cohort import CohortExpression
from circe.cohortdefinition.cohort_expression_query_builder import CohortExpressionQueryBuilder, BuildExpressionQueryOptions
from circe.cohortdefinition.criteria import PrimaryCriteria, VisitOccurrence

class TestBasePopulation(unittest.TestCase):
    def test_base_population_join(self):
        # Create a simple cohort
        expression = CohortExpression(
            PrimaryCriteria=PrimaryCriteria(
                CriteriaList=[
                    {'VisitOccurrence': {'CodesetId': 1}}
                ],
                ObservationWindow={'PriorDays': 0, 'PostDays': 0},
                PrimaryLimit={'Type': 'All'}
            )
        )
        
        # Build query WITH base population options
        builder = CohortExpressionQueryBuilder()
        options = BuildExpressionQueryOptions()
        options.base_population_table = "my_cohort"
        options.base_population_id = 123
        
        query = builder.build_expression_query(expression, options)
        
        # Verify JOIN exists with default schema placeholder
        expected_join = "JOIN @cohort_database_schema.@base_population_table BP ON E.person_id = BP.subject_id AND BP.population_id = @base_population_id"
        self.assertIn(expected_join, query)

    def test_base_population_join_with_schema(self):
        # Create a simple cohort
        expression = CohortExpression(
            PrimaryCriteria=PrimaryCriteria(
                CriteriaList=[
                    {'VisitOccurrence': {'CodesetId': 1}}
                ],
                ObservationWindow={'PriorDays': 0, 'PostDays': 0},
                PrimaryLimit={'Type': 'All'}
            )
        )
        
        # Build query WITH base population options AND schema
        builder = CohortExpressionQueryBuilder()
        options = BuildExpressionQueryOptions()
        options.base_population_table = "my_cohort"
        options.base_population_id = 123
        options.base_population_schema = "population_schema"
        
        query = builder.build_expression_query(expression, options)
        
        # Verify JOIN exists with CUSTOM schema placeholder
        expected_join = "JOIN @base_population_schema.@base_population_table BP ON E.person_id = BP.subject_id AND BP.population_id = @base_population_id"
        self.assertIn(expected_join, query)

    def test_no_base_population_join(self):
        # Create a simple cohort without base population options
        expression = CohortExpression(
            PrimaryCriteria=PrimaryCriteria(
                CriteriaList=[
                    {'VisitOccurrence': {'CodesetId': 1}}
                ],
                ObservationWindow={'PriorDays': 0, 'PostDays': 0},
                PrimaryLimit={'Type': 'All'}
            )
        )
        
        # Build query WITHOUT base population options
        builder = CohortExpressionQueryBuilder()
        options = BuildExpressionQueryOptions()
        
        query = builder.build_expression_query(expression, options)
        
        # Verify JOIN does NOT exist
        # We check for the alias used in the join implementation
        self.assertNotIn("BP.population_id", query)
        
        # Check standard parts are there
        self.assertIn("JOIN @cdm_database_schema.observation_period OP", query)

if __name__ == '__main__':
    unittest.main()
