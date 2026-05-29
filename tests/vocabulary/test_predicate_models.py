"""Tests for predicate expression models, ConceptPredicateItem, and backward compatibility."""

import json
import unittest
from pathlib import Path

from circe.vocabulary.concept import (
    Concept,
    ConceptExpressionItem,
    ConceptSet,
    ConceptSetExpression,
)
from circe.vocabulary.predicate_expressions import (
    HierarchyDescend,
    PredicateExpression,
    SetOperation,
    SetOperationNode,
    StringFilter,
    VocabularyScope,
)
from circe.vocabulary.predicate_item import ConceptPredicateItem


class TestPredicateExpressionModels(unittest.TestCase):
    """Test instantiation and validation of predicate expression types."""

    def test_vocabulary_scope_defaults(self):
        vs = VocabularyScope(vocabulary_id="SNOMED")
        self.assertEqual(vs.type, "vocabulary_scope")
        self.assertEqual(vs.vocabulary_id, "SNOMED")
        self.assertIsNone(vs.domain_id)
        self.assertEqual(vs.standard_concept, "S")

    def test_vocabulary_scope_all_fields(self):
        vs = VocabularyScope(
            vocabulary_id="SNOMED",
            domain_id="Condition",
            concept_class_id="Clinical Finding",
            standard_concept="S",
        )
        self.assertEqual(vs.domain_id, "Condition")
        self.assertEqual(vs.concept_class_id, "Clinical Finding")

    def test_hierarchy_descend_defaults(self):
        hd = HierarchyDescend(ancestor_concept_id=201820)
        self.assertEqual(hd.ancestor_concept_id, 201820)
        self.assertTrue(hd.include_ancestor)
        self.assertIsNone(hd.max_depth)

    def test_hierarchy_descend_with_max_depth(self):
        hd = HierarchyDescend(ancestor_concept_id=201820, max_depth=1)
        self.assertEqual(hd.max_depth, 1)

    def test_string_filter_defaults(self):
        sf = StringFilter(pattern="%diabetes%")
        self.assertEqual(sf.match_type, "ILIKE")
        self.assertIsNone(sf.scope)

    def test_string_filter_with_scope(self):
        scope = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        sf = StringFilter(pattern="%diabetes%", scope=scope)
        self.assertIsNotNone(sf.scope)
        self.assertEqual(sf.scope.vocabulary_id, "SNOMED")

    def test_set_operation_empty_operands(self):
        # Valid as a model, validation at application layer
        son = SetOperationNode(operation=SetOperation.UNION, operands=[])
        self.assertEqual(len(son.operands), 0)

    def test_set_operation_nested(self):
        inner = SetOperationNode(
            operation=SetOperation.INTERSECT,
            operands=[
                VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition"),
                HierarchyDescend(ancestor_concept_id=201820),
            ],
        )
        outer = SetOperationNode(
            operation=SetOperation.MINUS,
            operands=[
                inner,
                StringFilter(pattern="%gestational%"),
            ],
        )
        self.assertEqual(outer.operation, SetOperation.MINUS)
        self.assertEqual(len(outer.operands), 2)
        self.assertIsInstance(outer.operands[0], SetOperationNode)
        self.assertIsInstance(outer.operands[1], StringFilter)

    def test_predicate_expression_union_type(self):
        expr: PredicateExpression = VocabularyScope(vocabulary_id="RxNorm")
        self.assertIsInstance(expr, VocabularyScope)
        expr2: PredicateExpression = HierarchyDescend(ancestor_concept_id=123)
        self.assertIsInstance(expr2, HierarchyDescend)
        expr3: PredicateExpression = StringFilter(pattern="%aspirin%")
        self.assertIsInstance(expr3, StringFilter)
        expr4: PredicateExpression = SetOperationNode(
            operation=SetOperation.UNION, operands=[expr, expr2]
        )
        self.assertIsInstance(expr4, SetOperationNode)


class TestConceptPredicateItem(unittest.TestCase):
    """Test ConceptPredicateItem model."""

    def test_basic_predicate_item(self):
        expr = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        item = ConceptPredicateItem(name="All SNOMED conditions", expression=expr)
        self.assertEqual(item.type, "predicate_item")
        self.assertEqual(item.name, "All SNOMED conditions")
        self.assertFalse(item.is_excluded)

    def test_predicate_item_excluded(self):
        expr = HierarchyDescend(ancestor_concept_id=315295)
        item = ConceptPredicateItem(isExcluded=True, expression=expr)
        self.assertTrue(item.is_excluded)

    def test_predicate_item_serialization(self):
        expr = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        item = ConceptPredicateItem(expression=expr)
        data = item.model_dump(by_alias=True)
        self.assertEqual(data["type"], "predicate_item")
        self.assertIn("isExcluded", data)
        self.assertIn("expression", data)
        self.assertEqual(data["expression"]["vocabulary_id"], "SNOMED")

    def test_predicate_item_deserialization(self):
        raw = {
            "type": "predicate_item",
            "name": "Test",
            "isExcluded": True,
            "expression": {
                "type": "hierarchy_descend",
                "ancestor_concept_id": 201820,
                "include_ancestor": False,
            },
        }
        item = ConceptPredicateItem.model_validate(raw)
        self.assertEqual(item.name, "Test")
        self.assertTrue(item.is_excluded)
        self.assertIsInstance(item.expression, HierarchyDescend)
        self.assertEqual(item.expression.ancestor_concept_id, 201820)


class TestConceptSetExpressionMixedItems(unittest.TestCase):
    """Test ConceptSetExpression with mixed traditional and predicate items."""

    def setUp(self):
        self.traditional_item = ConceptExpressionItem(
            concept=Concept(concept_id=201826, concept_name="Type 2 diabetes"),
            isExcluded=False,
        )
        self.predicate_item = ConceptPredicateItem(
            name="All SNOMED conditions",
            expression=VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition"),
            isExcluded=False,
        )

    def test_mixed_items_list(self):
        expr = ConceptSetExpression(items=[self.traditional_item, self.predicate_item])
        self.assertEqual(len(expr.items), 2)
        self.assertIsInstance(expr.items[0], ConceptExpressionItem)
        self.assertIsInstance(expr.items[1], ConceptPredicateItem)

    def test_mixed_items_serialize_roundtrip(self):
        expr = ConceptSetExpression(items=[self.traditional_item, self.predicate_item])
        json_str = expr.model_dump_json(by_alias=True)
        restored = ConceptSetExpression.model_validate_json(json_str)
        self.assertEqual(len(restored.items), 2)
        self.assertIsInstance(restored.items[0], ConceptExpressionItem)
        self.assertIsInstance(restored.items[1], ConceptPredicateItem)
        self.assertEqual(
            restored.items[0].concept.concept_id,
            self.traditional_item.concept.concept_id,
        )
        self.assertEqual(
            restored.items[1].expression.vocabulary_id,
            self.predicate_item.expression.vocabulary_id,
        )

    def test_traditional_only_items_backward_compat(self):
        """Traditional ConceptExpressionItem without 'type' field loads correctly."""
        data = {
            "items": [
                {
                    "concept": {"CONCEPT_ID": 201826, "CONCEPT_NAME": "Diabetes"},
                    "isExcluded": False,
                    "includeDescendants": True,
                    "includeMapped": False,
                }
            ]
        }
        expr = ConceptSetExpression.model_validate(data)
        self.assertEqual(len(expr.items), 1)
        self.assertIsInstance(expr.items[0], ConceptExpressionItem)
        self.assertEqual(expr.items[0].concept.concept_id, 201826)


class TestLegacyFixtureBackwardCompat(unittest.TestCase):
    """Verify all existing JSON fixtures still load correctly."""

    @classmethod
    def setUpClass(cls):
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "schemas"
        cls.fixtures = {}
        for name in ["concept_set_legacy", "concept_set_new_schema", "concept_set_simple", "concept_set_minimal"]:
            with open(fixtures_dir / f"{name}.json") as f:
                cls.fixtures[name] = json.load(f)

    def test_legacy_loads(self):
        cs = ConceptSet.model_validate(self.fixtures["concept_set_legacy"])
        self.assertEqual(len(cs.expression.items), 2)
        self.assertIsInstance(cs.expression.items[0], ConceptExpressionItem)

    def test_new_schema_loads(self):
        cs = ConceptSet.model_validate(self.fixtures["concept_set_new_schema"])
        self.assertEqual(len(cs.expression.items), 2)
        self.assertIsInstance(cs.expression.items[0], ConceptExpressionItem)

    def test_simple_loads(self):
        cs = ConceptSet.model_validate(self.fixtures["concept_set_simple"])
        self.assertEqual(len(cs.expression.items), 1)
        self.assertIsInstance(cs.expression.items[0], ConceptExpressionItem)

    def test_minimal_loads(self):
        cs = ConceptSet.model_validate(self.fixtures["concept_set_minimal"])
        self.assertIsNotNone(cs.expression.items)
        self.assertIsInstance(cs.expression.items[0], ConceptExpressionItem)
