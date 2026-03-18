import unittest

from circe.cohortdefinition.criteria import CriteriaGroup
from circe.evaluation.builder import EvaluationBuilder
from circe.evaluation.engine import EvaluationQueryBuilder
from circe.evaluation.models import EvaluationRubric


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
        with (
            EvaluationBuilder("Complex Rubric") as ev,
            ev.rule("Multi-match", weight=10) as rule,
            rule.any_of() as any_group,
        ):
            any_group.condition(1)
            any_group.drug(2)

        rubric = ev.rubric
        rule = rubric.rules[0]
        self.assertEqual(rule.expression.type, "ALL")  # Default root is ALL
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

    def test_within_days_symmetric_backwards_compatibility(self):
        """Test that within_days(N) still creates a symmetric window."""
        with EvaluationBuilder("Symmetric") as ev:
            ev.add_rule("Rule", weight=1).condition(1).within_days(5)

        rule = ev.rubric.rules[0]
        window = rule.expression.criteria_list[0].start_window
        self.assertEqual(window.start.days, 5)
        self.assertEqual(window.start.coeff, -1)
        self.assertEqual(window.end.days, 5)
        self.assertEqual(window.end.coeff, 1)

    def test_within_days_asymmetric_explicit(self):
        """Test within_days(before=X, after=Y)."""
        with EvaluationBuilder("Asymmetric") as ev:
            ev.add_rule("Rule", weight=1).condition(1).within_days(before=7, after=14)

        rule = ev.rubric.rules[0]
        window = rule.expression.criteria_list[0].start_window
        self.assertEqual(window.start.days, 7)
        self.assertEqual(window.start.coeff, -1)
        self.assertEqual(window.end.days, 14)
        self.assertEqual(window.end.coeff, 1)

    def test_within_days_before_only(self):
        """Test within_days(before=X)."""
        with EvaluationBuilder("BeforeOnly") as ev:
            ev.add_rule("Rule", weight=1).condition(1).within_days(before=10)

        rule = ev.rubric.rules[0]
        window = rule.expression.criteria_list[0].start_window
        self.assertEqual(window.start.days, 10)
        self.assertEqual(window.start.coeff, -1)
        self.assertEqual(window.end.days, 0)
        self.assertEqual(window.end.coeff, 1)

    def test_within_days_after_only(self):
        """Test within_days(after=X)."""
        with EvaluationBuilder("AfterOnly") as ev:
            ev.add_rule("Rule", weight=1).condition(1).within_days(after=10)

        rule = ev.rubric.rules[0]
        window = rule.expression.criteria_list[0].start_window
        self.assertEqual(window.start.days, 0)
        self.assertEqual(window.start.coeff, -1)
        self.assertEqual(window.end.days, 10)
        self.assertEqual(window.end.coeff, 1)

    def test_priority_days_over_before_after(self):
        """Test that 'days' argument takes precedence if provided."""
        with EvaluationBuilder("Priority") as ev:
            # Should be symmetric 5, ignoring before=10/after=10
            ev.add_rule("Rule", weight=1).condition(1).within_days(days=5, before=10, after=10)

        rule = ev.rubric.rules[0]
        window = rule.expression.criteria_list[0].start_window
        self.assertEqual(window.start.days, 5)
        self.assertEqual(window.end.days, 5)


if __name__ == "__main__":
    unittest.main()
