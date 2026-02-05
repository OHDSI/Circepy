"""
Unit tests for Phenotype Evaluation Framework.
"""

import unittest
import json
from circe.evaluation.models import EvaluationRule, EvaluationRubric, IndividualEvaluation
from circe.evaluation.engine import EvaluationQueryBuilder
from examples.evaluation.gi_bleed_prototype import create_gi_bleed_rubric
from circe.vocabulary import concept_set, descendants
from circe.cohortdefinition.criteria import ConditionOccurrence, CorelatedCriteria


class TestEvaluationModels(unittest.TestCase):
    def test_rubric_serialization(self):
        rubric = create_gi_bleed_rubric()
        json_str = rubric.model_dump_json()
        data = json.loads(json_str)
        
        self.assertIn("Rules", data)
        self.assertIn("ConceptSets", data)
        self.assertEqual(len(data["Rules"]), 3)
        self.assertEqual(len(data["ConceptSets"]), 3)


    def test_individual_evaluation_model(self):
        eval_result = IndividualEvaluation(
            subject_id=123,
            index_date="2023-01-01",
            ruleset_id=1,
            total_score=15.5,
            rules=[
                {
                    "rule_id": 1,
                    "rule_name": "Test Rule",
                    "score": 10.0,
                    "matched": True,
                    "category": "Primary"
                }
            ]
        )
        self.assertEqual(eval_result.subject_id, 123)
        self.assertEqual(len(eval_result.rules), 1)


class TestEvaluationEngine(unittest.TestCase):
    def setUp(self):
        self.builder = EvaluationQueryBuilder()

    def test_gi_bleed_sql_generation(self):
        rubric = create_gi_bleed_rubric()
        sql = self.builder.build_query(rubric, ruleset_id=1)
        
        # Check for key SQL components
        self.assertIn("CREATE TABLE #Codesets", sql)
        self.assertIn("INSERT INTO #Codesets", sql)
        self.assertIn("192671", sql) # GI hemorrhage
        
        # Check for target table population
        self.assertIn("DELETE FROM @results_database_schema.cohort_rubric WHERE ruleset_id = 1", sql)
        self.assertIn("INSERT INTO @results_database_schema.cohort_rubric (ruleset_id, subject_id, index_date, rule_id, score)", sql)
        
        self.assertIn("ruleset_id", sql)
        self.assertIn("subject_id", sql)
        self.assertIn("index_date", sql)
        self.assertIn("rule_id", sql)
        self.assertIn("UNION ALL", sql)
        self.assertIn("LEFT JOIN", sql)
        self.assertIn("CONDITION_OCCURRENCE", sql)
        self.assertIn("PROCEDURE_OCCURRENCE", sql)
        self.assertIn("MEASUREMENT", sql)

    def test_single_rule_sql(self):
        gi_hemorrhage_cs = concept_set(descendants(192671), id=1, name="GI Hemorrhage")
        rule = EvaluationRule(
            rule_id=1,
            name="GI Hemorrhage",
            criteria=CorelatedCriteria(
                criteria=ConditionOccurrence(codeset_id=gi_hemorrhage_cs.id)
            ),
            weight=10.0,
            category="Primary"
        )
        rubric = EvaluationRubric(
            concept_sets=[gi_hemorrhage_cs],
            rules=[rule]
        )
        
        sql = self.builder.build_query(rubric, ruleset_id=99, target_table="my_custom_table")
        
        self.assertIn("DELETE FROM @results_database_schema.my_custom_table WHERE ruleset_id = 99", sql)
        self.assertIn("INSERT INTO @results_database_schema.my_custom_table", sql)
        self.assertIn("99 as ruleset_id", sql)
        self.assertIn("10.0 * 1 as score", sql)

    def test_ddl_generation(self):
        ddl = self.builder.get_ddl(results_schema="results", target_table="eval_table")
        self.assertIn("CREATE TABLE results.eval_table", ddl)
        self.assertIn("ruleset_id INT", ddl)
        self.assertIn("subject_id BIGINT", ddl)
        self.assertIn("index_date DATE", ddl)
        self.assertIn("rule_id INT", ddl)
        self.assertIn("score FLOAT", ddl)



if __name__ == "__main__":
    unittest.main()
