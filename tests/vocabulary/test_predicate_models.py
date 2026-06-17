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
    ConceptCodeFilter,
    ConceptDateFilter,
    ConceptIdRange,
    ConceptSynonymFilter,
    HierarchyAscend,
    HierarchyDescend,
    ImmediateChildren,
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
        expr4: PredicateExpression = SetOperationNode(operation=SetOperation.UNION, operands=[expr, expr2])
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
        for name in [
            "concept_set_legacy",
            "concept_set_new_schema",
            "concept_set_simple",
            "concept_set_minimal",
        ]:
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


class TestNewExpressionModels(unittest.TestCase):
    """Test new predicate expression types."""

    def test_concept_code_filter_exact(self):
        ccf = ConceptCodeFilter(codes=["E11.9", "E10.0"])
        self.assertEqual(ccf.type, "concept_code_filter")
        self.assertEqual(ccf.match_type, "exact")
        self.assertEqual(len(ccf.codes), 2)

    def test_concept_code_filter_like(self):
        ccf = ConceptCodeFilter(codes=["E11%"], match_type="LIKE")
        self.assertEqual(ccf.match_type, "LIKE")

    def test_concept_code_filter_regex(self):
        ccf = ConceptCodeFilter(codes=["E1[0-9]"], match_type="REGEX")
        self.assertEqual(ccf.match_type, "REGEX")

    def test_concept_code_filter_with_scope(self):
        scope = VocabularyScope(vocabulary_id="ICD10CM")
        ccf = ConceptCodeFilter(codes=["E11%"], match_type="LIKE", scope=scope)
        self.assertIsNotNone(ccf.scope)
        self.assertEqual(ccf.scope.vocabulary_id, "ICD10CM")

    def test_concept_synonym_filter_defaults(self):
        csf = ConceptSynonymFilter(pattern="%heart attack%")
        self.assertEqual(csf.type, "concept_synonym_filter")
        self.assertEqual(csf.match_type, "ILIKE")

    def test_concept_synonym_filter_regex(self):
        csf = ConceptSynonymFilter(pattern="heart (attack|failure)", match_type="REGEX")
        self.assertEqual(csf.match_type, "REGEX")

    def test_hierarchy_ascend_defaults(self):
        ha = HierarchyAscend(descendant_concept_id=201820)
        self.assertEqual(ha.type, "hierarchy_ascend")
        self.assertEqual(ha.descendant_concept_id, 201820)
        self.assertTrue(ha.include_descendant)
        self.assertIsNone(ha.max_depth)

    def test_hierarchy_ascend_exclude_descendant(self):
        ha = HierarchyAscend(descendant_concept_id=201820, include_descendant=False)
        self.assertFalse(ha.include_descendant)

    def test_immediate_children(self):
        ic = ImmediateChildren(ancestor_concept_id=201820)
        self.assertEqual(ic.type, "immediate_children")
        self.assertEqual(ic.ancestor_concept_id, 201820)

    def test_concept_id_range_both(self):
        cir = ConceptIdRange(min_id=1000000, max_id=2000000)
        self.assertEqual(cir.type, "concept_id_range")
        self.assertEqual(cir.min_id, 1000000)
        self.assertEqual(cir.max_id, 2000000)

    def test_concept_id_range_min_only(self):
        cir = ConceptIdRange(min_id=4000000)
        self.assertIsNotNone(cir.min_id)
        self.assertIsNone(cir.max_id)

    def test_concept_date_filter_valid_on(self):
        cdf = ConceptDateFilter(valid_on_date="2024-01-01")
        self.assertEqual(cdf.type, "concept_date_filter")
        self.assertEqual(cdf.valid_on_date, "2024-01-01")

    def test_concept_date_filter_all_fields(self):
        cdf = ConceptDateFilter(
            valid_start_date="2020-01-01",
            valid_end_date="2024-12-31",
        )
        self.assertEqual(cdf.valid_start_date, "2020-01-01")
        self.assertEqual(cdf.valid_end_date, "2024-12-31")

    def test_new_types_in_predicate_expression_union(self):
        expr: PredicateExpression = ConceptCodeFilter(codes=["E11%"])
        self.assertIsInstance(expr, ConceptCodeFilter)
        expr2: PredicateExpression = ConceptSynonymFilter(pattern="%diabetes%")
        self.assertIsInstance(expr2, ConceptSynonymFilter)
        expr3: PredicateExpression = HierarchyAscend(descendant_concept_id=123)
        self.assertIsInstance(expr3, HierarchyAscend)
        expr4: PredicateExpression = ImmediateChildren(ancestor_concept_id=123)
        self.assertIsInstance(expr4, ImmediateChildren)
        expr5: PredicateExpression = ConceptIdRange(min_id=1, max_id=100)
        self.assertIsInstance(expr5, ConceptIdRange)
        expr6: PredicateExpression = ConceptDateFilter(valid_on_date="2024-01-01")
        self.assertIsInstance(expr6, ConceptDateFilter)

    def test_new_types_serialize_roundtrip(self):
        for expr, expected_type in [
            (ConceptCodeFilter(codes=["E11.9"]), ConceptCodeFilter),
            (ConceptSynonymFilter(pattern="%heart%"), ConceptSynonymFilter),
            (HierarchyAscend(descendant_concept_id=201820), HierarchyAscend),
            (ImmediateChildren(ancestor_concept_id=201820), ImmediateChildren),
            (ConceptIdRange(min_id=1, max_id=100), ConceptIdRange),
            (ConceptDateFilter(valid_on_date="2024-01-01"), ConceptDateFilter),
        ]:
            json_str = expr.model_dump_json(by_alias=True)
            restored = expected_type.model_validate_json(json_str)
            self.assertIsInstance(restored, expected_type)

    def test_new_types_in_predicate_item(self):
        items = [
            ConceptPredicateItem(
                name="ICD codes",
                expression=ConceptCodeFilter(codes=["E11%"], match_type="LIKE"),
            ),
            ConceptPredicateItem(
                name="Synonym search",
                expression=ConceptSynonymFilter(pattern="%heart%"),
            ),
            ConceptPredicateItem(
                name="Hierarchy ascend",
                expression=HierarchyAscend(descendant_concept_id=201820),
            ),
            ConceptPredicateItem(
                name="Immediate children",
                expression=ImmediateChildren(ancestor_concept_id=201820),
            ),
            ConceptPredicateItem(
                name="ID range",
                expression=ConceptIdRange(min_id=1, max_id=100),
            ),
            ConceptPredicateItem(
                name="Date filter",
                expression=ConceptDateFilter(valid_on_date="2024-01-01"),
            ),
        ]
        for item in items:
            self.assertIsInstance(item, ConceptPredicateItem)
            self.assertEqual(item.type, "predicate_item")

        expr = ConceptSetExpression(items=items)
        self.assertEqual(len(expr.items), 6)
        json_str = expr.model_dump_json(by_alias=True)
        restored = ConceptSetExpression.model_validate_json(json_str)
        self.assertEqual(len(restored.items), 6)
        for restored_item in restored.items:
            self.assertIsInstance(restored_item, ConceptPredicateItem)
