"""Tests for the predicate validator."""

import unittest

from circe.vocabulary.concept import ConceptSetExpression
from circe.vocabulary.predicate_expressions import (
    HierarchyDescend,
    SetOperation,
    SetOperationNode,
    StringFilter,
    VocabularyScope,
)
from circe.vocabulary.predicate_item import ConceptPredicateItem
from circe.vocabulary.predicate_validator import PredicateValidator


class TestPredicateValidator(unittest.TestCase):
    """Test each validation rule triggers correctly."""

    @classmethod
    def setUpClass(cls):
        cls.validator = PredicateValidator()

    def test_no_items_error(self):
        cs = ConceptSetExpression(items=[])
        warnings = self.validator.validate(cs)
        self.assertTrue(any(w.level == "error" and "no items" in w.message.lower() for w in warnings))

    def test_all_excluded_warning(self):
        item = ConceptPredicateItem(
            expression=VocabularyScope(vocabulary_id="SNOMED"),
            isExcluded=True,
        )
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any(w.level == "warning" and "all items" in w.message.lower() for w in warnings))

    def test_mixed_included_and_excluded_no_warning(self):
        inc = ConceptPredicateItem(
            expression=VocabularyScope(vocabulary_id="SNOMED"), isExcluded=False
        )
        exc = ConceptPredicateItem(
            expression=VocabularyScope(vocabulary_id="ICD10CM"), isExcluded=True
        )
        cs = ConceptSetExpression(items=[inc, exc])
        warnings = self.validator.validate(cs)
        self.assertFalse(any("all items" in w.message.lower() for w in warnings))

    def test_unbounded_vocabulary_scope_warning(self):
        expr = VocabularyScope(vocabulary_id="SNOMED")
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any("no domain_id" in w.message.lower() for w in warnings))

    def test_scoped_vocabulary_no_warning(self):
        expr = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertFalse(any("no domain_id" in w.message.lower() for w in warnings))

    def test_hierarchy_negative_depth_error(self):
        expr = HierarchyDescend(ancestor_concept_id=201820, max_depth=0)
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any("max_depth" in w.message.lower() and w.level == "error" for w in warnings))

    def test_hierarchy_valid_depth_no_warning(self):
        expr = HierarchyDescend(ancestor_concept_id=201820, max_depth=1)
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertFalse(any("max_depth" in w.message.lower() for w in warnings))

    def test_string_filter_empty_pattern_error(self):
        expr = StringFilter(pattern="")
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any("empty" in w.message.lower() and w.level == "error" for w in warnings))

    def test_string_filter_wildcard_only_error(self):
        expr = StringFilter(pattern="%")
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any("wildcard" in w.message.lower() and w.level == "error" for w in warnings))

    def test_string_filter_double_wildcard_error(self):
        expr = StringFilter(pattern="%%")
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any("wildcard" in w.message.lower() and w.level == "error" for w in warnings))

    def test_string_filter_short_pattern_warning(self):
        expr = StringFilter(pattern="%a%")
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any("short" in w.message.lower() and w.level == "warning" for w in warnings))

    def test_string_filter_short_with_scope_no_warning(self):
        scope = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        expr = StringFilter(pattern="%a%", scope=scope)
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertFalse(any("short" in w.message.lower() for w in warnings))

    def test_set_operation_empty_operands_error(self):
        expr = SetOperationNode(operation=SetOperation.UNION, operands=[])
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any("operands" in w.message.lower() and w.level == "error" for w in warnings))

    def test_set_operation_single_operand_error(self):
        expr = SetOperationNode(
            operation=SetOperation.UNION,
            operands=[VocabularyScope(vocabulary_id="SNOMED")],
        )
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertTrue(any("operands" in w.message.lower() and w.level == "error" for w in warnings))

    def test_set_operation_two_operands_valid(self):
        expr = SetOperationNode(
            operation=SetOperation.UNION,
            operands=[
                VocabularyScope(vocabulary_id="SNOMED"),
                VocabularyScope(vocabulary_id="ICD10CM"),
            ],
        )
        item = ConceptPredicateItem(expression=expr)
        cs = ConceptSetExpression(items=[item])
        warnings = self.validator.validate(cs)
        self.assertFalse(any("operands" in w.message.lower() for w in warnings))

    def test_valid_predicate_no_warnings(self):
        expr = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition", concept_class_id="Clinical Finding")
        item = ConceptPredicateItem(expression=expr, isExcluded=False)
        item2 = ConceptPredicateItem(expression=StringFilter(pattern="%diabetes%"), isExcluded=False)
        cs = ConceptSetExpression(items=[item, item2])
        warnings = self.validator.validate(cs)
        errors = [w for w in warnings if w.level == "error"]
        self.assertEqual(len(errors), 0)
