import unittest
from circe.evaluation.builder import EvaluationBuilder
from circe.evaluation.engine import EvaluationQueryBuilder
from circe.evaluation.models import EvaluationRubric, EvaluationRule
from circe.cohortdefinition.criteria import CriteriaGroup

class TestEvaluationBuilder(unittest.TestCase):

    def test_basic_rubric_building(self):
        """Test building a simple rubric with one rule."""
        with EvaluationBuilder("Basic Rubric") as ev:
            ev.add_rule("GI Bleed", weight=10).condition(192671)
        
        rubric = ev.rubric
        self.assertIsInstance(rubric, EvaluationRubric)
        self.assertEqual(len(rubric.rules), 1)
        self.assertEqual(rubric.rules[0].name, "GI Bleed")
        self.assertEqual(rubric.rules[0].weight, 10)
        self.assertIsInstance(rubric.rules[0].expression, CriteriaGroup)

    def test_measurement_with_value(self):
        """Test rule with measurement and value range."""
        with EvaluationBuilder("Measurement Rubric") as ev:
            ev.add_rule("High Glucose", weight=5).measurement(3004410).with_value(gt=126)
            
        rubric = ev.rubric
        rule = rubric.rules[0]
        # Check that the underlying criteria has the value range
        criteria = rule.expression.criteria_list[0].criteria
        self.assertEqual(criteria.value_as_number.value, 126)
        self.assertEqual(criteria.value_as_number.op, "gte")

    def test_complex_rule(self):
        """Test rule with nested logical grouping."""
        with EvaluationBuilder("Complex Rubric") as ev:
            with ev.rule("Multi-match", weight=10) as rule:
                with rule.any_of() as any_group:
                    any_group.condition(1)
                    any_group.drug(2)
        
        rubric = ev.rubric
        rule = rubric.rules[0]
        self.assertEqual(rule.expression.type, "ALL") # Default root is ALL
        self.assertEqual(len(rule.expression.groups), 1)
        self.assertEqual(rule.expression.groups[0].type, "ANY")
        self.assertEqual(len(rule.expression.groups[0].criteria_list), 2)

    def test_sql_generation(self):
        """Test that EvaluationQueryBuilder handles the new rule structure."""
        with EvaluationBuilder("SQL Test") as ev:
            ev.add_rule("Rule 1", weight=10).condition(1)
            
        rubric = ev.rubric
        builder = EvaluationQueryBuilder()
        sql = builder.build_query(rubric, ruleset_id=1)
        
        # Basic sanity checks on generated SQL
        self.assertIn("Rule 1", str(rubric.rules[0].name))
        self.assertIn("CAST(COALESCE(R.score, 0) AS FLOAT)", sql)
        self.assertIn("person_id", sql)

if __name__ == "__main__":
    unittest.main()
