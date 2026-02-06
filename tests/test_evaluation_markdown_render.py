import unittest
import json
from circe.evaluation.markdown_render import EvaluationMarkdownRender
from circe.evaluation.models import EvaluationRubric, EvaluationRule
from circe.cohortdefinition.criteria import CriteriaGroup, CorelatedCriteria, ConditionOccurrence, Occurrence
from circe.vocabulary import ConceptSet

class TestEvaluationMarkdownRender(unittest.TestCase):
    def setUp(self):
        self.renderer = EvaluationMarkdownRender()

    def test_render_invalid_rubric(self):
        # Test with invalid JSON string - should raise or be handled
        # The current implementation calls model_validate_json which raises ValidationError
        with self.assertRaises(Exception):
            self.renderer.render_rubric("{ invalid json }")

    def test_render_empty_rubric(self):
        # Test with rubric having no rules
        rubric = EvaluationRubric(rules=[])
        result = self.renderer.render_rubric(rubric)
        self.assertIn("# Evaluation Rubric", result)
        self.assertIn("## Summary of Rules", result)
        self.assertIn("## Rule Details", result)
        # Verify no rules are listed in the table
        self.assertNotIn("| 1 |", result)

    def test_render_basic_rubric(self):
        # Create a simple rubric with one rule
        rule = EvaluationRule(
            rule_id=1,
            name="Test Rule",
            weight=10.0,
            polarity=1,
            category="Primary",
            expression=CriteriaGroup()
        )
        rubric = EvaluationRubric(rules=[rule])
        
        result = self.renderer.render_rubric(rubric, title="Custom Title")
        
        self.assertIn("# Custom Title", result)
        self.assertIn("| 1 | Test Rule | 10 | Evidence | Primary |", result)
        self.assertIn("### 1. Test Rule", result)
        self.assertIn("**Weight:** 10", result)
        self.assertIn("**Mode:** Positive (Evidence)", result)
        self.assertIn("**Category:** Primary", result)

    def test_render_rubric_with_polarity_exclusion(self):
        # Create a rubric with an exclusion rule
        rule = EvaluationRule(
            rule_id=2,
            name="Exclusion Rule",
            weight=5.5,
            polarity=-1,
            expression=CriteriaGroup()
        )
        rubric = EvaluationRubric(rules=[rule])
        
        result = self.renderer.render_rubric(rubric)
        
        self.assertIn("| 2 | Exclusion Rule | 5.5 | Exclusion | - |", result)
        self.assertIn("**Mode:** Negative (Exclusion)", result)

    def test_render_rubric_with_concept_sets(self):
        # Create a rubric with concept sets
        cs = ConceptSet(id=1, name="My Concept Set", expression={"items": []})
        
        rule = EvaluationRule(
            rule_id=1,
            name="CS Rule",
            weight=1.0,
            polarity=1,
            expression=CriteriaGroup()
        )
        rubric = EvaluationRubric(rules=[rule], concept_sets=[cs])
        
        result = self.renderer.render_rubric(rubric)
        
        self.assertIn("## Concept Sets", result)
        # The header in concept_set.j2 is just "### {{ cs.name }}"
        self.assertIn("### My Concept Set", result)

    def test_render_complex_expression(self):
        # Create a more complex expression
        # ConditionOccurrence on CS 101
        m_criteria = ConditionOccurrence(codeset_id=101)
        corelated = CorelatedCriteria(
            criteria=m_criteria,
            occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1)
        )
        group = CriteriaGroup(criteria_list=[corelated])
        
        rule = EvaluationRule(
            rule_id=1,
            name="Complex Rule",
            weight=1.0,
            polarity=1,
            expression=group
        )
        
        # Provide concept sets to help resolver
        cs = ConceptSet(id=101, name="Heart Failure", expression={"items": []})
        rubric = EvaluationRubric(rules=[rule], concept_sets=[cs])
        
        result = self.renderer.render_rubric(rubric)
        
        # Check if the criteria details are rendered
        # ct.Group(rule.expression) should render something like "at least 1 condition occurrences of Heart Failure"
        self.assertIn("at least 1", result)
        # The codeset name should be resolved if concept sets are provided
        self.assertIn("'Heart Failure'", result)

    def test_render_json_string(self):
        # Test rendering from a JSON string
        rubric_json = json.dumps({
            "rules": [{
                "rule_id": 1,
                "name": "JSON Rule",
                "weight": 1.0,
                "polarity": 1,
                "expression": {"CriteriaList": [], "Groups": [], "DemographicCriteriaList": [], "Type": "ALL"}
            }]
        })
        
        result = self.renderer.render_rubric(rubric_json)
        self.assertIn("JSON Rule", result)

if __name__ == "__main__":
    unittest.main()
