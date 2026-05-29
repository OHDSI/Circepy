"""Tests for the predicate SQL compiler."""

import unittest

from circe.vocabulary.predicate_expressions import (
    HierarchyDescend,
    SetOperation,
    SetOperationNode,
    StringFilter,
    VocabularyScope,
)
from circe.vocabulary.predicate_sql_compiler import SCHEMA_PLACEHOLDER, PredicateSQLCompiler


class TestPredicateSQLCompiler(unittest.TestCase):
    """Test SQL output for each predicate expression type."""

    @classmethod
    def setUpClass(cls):
        cls.compiler = PredicateSQLCompiler()

    def test_vocabulary_scope_basic(self):
        expr = VocabularyScope(vocabulary_id="SNOMED")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("SELECT concept_id", sql)
        self.assertIn(f"FROM {SCHEMA_PLACEHOLDER}.CONCEPT", sql)
        self.assertIn("vocabulary_id = 'SNOMED'", sql)
        self.assertIn("invalid_reason IS NULL", sql)
        self.assertIn("standard_concept = 'S'", sql)

    def test_vocabulary_scope_with_domain(self):
        expr = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("domain_id = 'Condition'", sql)

    def test_vocabulary_scope_any_standard(self):
        expr = VocabularyScope(vocabulary_id="SNOMED", standard_concept="any")
        sql = self.compiler.compile_expression(expr)
        self.assertNotIn("standard_concept =", sql)

    def test_hierarchy_descend(self):
        expr = HierarchyDescend(ancestor_concept_id=201820)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("SELECT ca.descendant_concept_id", sql)
        self.assertIn("FROM", sql)
        self.assertIn("CONCEPT_ANCESTOR", sql)
        self.assertIn("ancestor_concept_id = 201820", sql)
        self.assertIn("invalid_reason IS NULL", sql)

    def test_hierarchy_descend_with_max_depth(self):
        expr = HierarchyDescend(ancestor_concept_id=201820, max_depth=1)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("min_levels_of_separation <= 1", sql)

    def test_hierarchy_descend_exclude_ancestor(self):
        expr = HierarchyDescend(ancestor_concept_id=201820, include_ancestor=False)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("min_levels_of_separation >= 1", sql)

    def test_hierarchy_descend_include_ancestor(self):
        expr = HierarchyDescend(ancestor_concept_id=201820, include_ancestor=True)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("min_levels_of_separation >= 0", sql)

    def test_string_filter_basic(self):
        expr = StringFilter(pattern="%diabetes%")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("ILIKE", sql)
        self.assertIn("%diabetes%", sql)
        self.assertIn("invalid_reason IS NULL", sql)

    def test_string_filter_like(self):
        expr = StringFilter(pattern="Diabetes", match_type="LIKE")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("LIKE", sql)
        self.assertNotIn("ILIKE", sql)

    def test_string_filter_with_scope(self):
        scope = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        expr = StringFilter(pattern="%heart%", scope=scope)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("vocabulary_id = 'SNOMED'", sql)
        self.assertIn("domain_id = 'Condition'", sql)
        self.assertIn("standard_concept = 'S'", sql)

    def test_set_operation_union(self):
        v1 = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        v2 = VocabularyScope(vocabulary_id="ICD10CM", domain_id="Condition")
        expr = SetOperationNode(operation=SetOperation.UNION, operands=[v1, v2])
        sql = self.compiler.compile_expression(expr)
        self.assertIn("UNION", sql)
        self.assertIn("SNOMED", sql)
        self.assertIn("ICD10CM", sql)

    def test_set_operation_intersect(self):
        v1 = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        hd = HierarchyDescend(ancestor_concept_id=201820)
        expr = SetOperationNode(operation=SetOperation.INTERSECT, operands=[v1, hd])
        sql = self.compiler.compile_expression(expr)
        self.assertIn("INTERSECT", sql)

    def test_set_operation_minus(self):
        hd1 = HierarchyDescend(ancestor_concept_id=201820)
        hd2 = HierarchyDescend(ancestor_concept_id=4058243)
        expr = SetOperationNode(operation=SetOperation.MINUS, operands=[hd1, hd2])
        sql = self.compiler.compile_expression(expr)
        self.assertIn("EXCEPT", sql)

    def test_set_operation_union_three(self):
        v1 = VocabularyScope(vocabulary_id="SNOMED")
        v2 = VocabularyScope(vocabulary_id="ICD10CM")
        v3 = VocabularyScope(vocabulary_id="RxNorm")
        expr = SetOperationNode(operation=SetOperation.UNION, operands=[v1, v2, v3])
        sql = self.compiler.compile_expression(expr)
        # Should contain all three vocabulary IDs
        self.assertIn("SNOMED", sql)
        self.assertIn("ICD10CM", sql)
        self.assertIn("RxNorm", sql)

    def test_nested_set_operation(self):
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
                HierarchyDescend(ancestor_concept_id=4058243),
            ],
        )
        sql = self.compiler.compile_expression(outer)
        self.assertIn("INTERSECT", sql)
        self.assertIn("EXCEPT", sql)
        # Proper nesting via parentheses
        self.assertTrue(sql.startswith("("))

    def test_concept_id_list(self):
        sql = self.compiler.compile_concept_id_list([1, 2, 3])
        self.assertIn("IN (1, 2, 3)", sql)

    def test_empty_operands_raises(self):
        expr = SetOperationNode(operation=SetOperation.UNION, operands=[])
        with self.assertRaises(ValueError):
            self.compiler.compile_expression(expr)
