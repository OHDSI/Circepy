"""Tests for the predicate SQL compiler."""

import unittest

from circe.vocabulary.predicate_expressions import (
    ConceptCodeFilter,
    ConceptDateFilter,
    ConceptIdRange,
    ConceptSynonymFilter,
    HierarchyAscend,
    HierarchyDescend,
    ImmediateChildren,
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

    # --- StringFilter REGEX ---

    def test_string_filter_regex(self):
        expr = StringFilter(pattern="^(type|Type)\\s+(1|2)", match_type="REGEX")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("~*", sql)
        self.assertIn("invalid_reason IS NULL", sql)

    def test_string_filter_regex_with_scope(self):
        scope = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        expr = StringFilter(pattern="diabetes", match_type="REGEX", scope=scope)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("~*", sql)
        self.assertIn("vocabulary_id = 'SNOMED'", sql)

    # --- ConceptCodeFilter ---

    def test_concept_code_filter_exact(self):
        expr = ConceptCodeFilter(codes=["E11.9", "E10.0"])
        sql = self.compiler.compile_expression(expr)
        self.assertIn("concept_code IN", sql)
        self.assertIn("'E11.9'", sql)
        self.assertIn("'E10.0'", sql)

    def test_concept_code_filter_like(self):
        expr = ConceptCodeFilter(codes=["E11%"], match_type="LIKE")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("LIKE", sql)
        self.assertIn("'E11%'", sql)

    def test_concept_code_filter_ilike(self):
        expr = ConceptCodeFilter(codes=["e11%"], match_type="ILIKE")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("ILIKE", sql)

    def test_concept_code_filter_regex(self):
        expr = ConceptCodeFilter(codes=["E1[0-9]\\..*"], match_type="REGEX")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("~*", sql)

    def test_concept_code_filter_multiple_like(self):
        expr = ConceptCodeFilter(codes=["E11%", "E10%"], match_type="ILIKE")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("OR", sql)
        self.assertIn("ILIKE", sql)

    def test_concept_code_filter_with_scope(self):
        scope = VocabularyScope(vocabulary_id="ICD10CM")
        expr = ConceptCodeFilter(codes=["E11%"], match_type="LIKE", scope=scope)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("vocabulary_id = 'ICD10CM'", sql)

    # --- ConceptSynonymFilter ---

    def test_concept_synonym_filter_ilike(self):
        expr = ConceptSynonymFilter(pattern="%heart attack%")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("CONCEPT_SYNONYM", sql)
        self.assertIn("ILIKE", sql)

    def test_concept_synonym_filter_like(self):
        expr = ConceptSynonymFilter(pattern="Heart Attack", match_type="LIKE")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("LIKE", sql)

    def test_concept_synonym_filter_regex(self):
        expr = ConceptSynonymFilter(pattern="heart (attack|failure)", match_type="REGEX")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("~*", sql)

    def test_concept_synonym_filter_with_scope(self):
        scope = VocabularyScope(vocabulary_id="SNOMED")
        expr = ConceptSynonymFilter(pattern="%heart%", scope=scope)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("CONCEPT_SYNONYM cs", sql)
        self.assertIn("JOIN", sql)
        self.assertIn("vocabulary_id = 'SNOMED'", sql)

    def test_concept_synonym_filter_no_scope_joins_for_invalid_reason(self):
        expr = ConceptSynonymFilter(pattern="%heart%")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("JOIN", sql)
        self.assertIn("CONCEPT_SYNONYM cs", sql)
        self.assertIn("c.invalid_reason IS NULL", sql)

    # --- HierarchyAscend ---

    def test_hierarchy_ascend(self):
        expr = HierarchyAscend(descendant_concept_id=201820)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("SELECT ca.ancestor_concept_id", sql)
        self.assertIn("CONCEPT_ANCESTOR", sql)
        self.assertIn("descendant_concept_id = 201820", sql)
        self.assertIn("min_levels_of_separation >= 0", sql)

    def test_hierarchy_ascend_exclude_descendant(self):
        expr = HierarchyAscend(descendant_concept_id=201820, include_descendant=False)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("min_levels_of_separation >= 1", sql)

    def test_hierarchy_ascend_with_max_depth(self):
        expr = HierarchyAscend(descendant_concept_id=201820, max_depth=1)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("min_levels_of_separation <= 1", sql)

    # --- ImmediateChildren ---

    def test_immediate_children(self):
        expr = ImmediateChildren(ancestor_concept_id=201820)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("min_levels_of_separation = 1", sql)
        self.assertIn("ancestor_concept_id = 201820", sql)
        self.assertIn("descendant_concept_id", sql)

    # --- ConceptIdRange ---

    def test_concept_id_range_both(self):
        expr = ConceptIdRange(min_id=1000000, max_id=2000000)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("BETWEEN 1000000 AND 2000000", sql)

    def test_concept_id_range_min_only(self):
        expr = ConceptIdRange(min_id=4000000)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("concept_id >= 4000000", sql)

    def test_concept_id_range_max_only(self):
        expr = ConceptIdRange(max_id=5000000)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("concept_id <= 5000000", sql)

    def test_concept_id_range_with_scope(self):
        scope = VocabularyScope(vocabulary_id="SNOMED")
        expr = ConceptIdRange(min_id=1, max_id=100000, scope=scope)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("BETWEEN", sql)
        self.assertIn("vocabulary_id = 'SNOMED'", sql)

    # --- ConceptDateFilter ---

    def test_concept_date_filter_valid_on(self):
        expr = ConceptDateFilter(valid_on_date="2024-01-01")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("valid_start_date <= '2024-01-01'", sql)
        self.assertIn("valid_end_date >= '2024-01-01'", sql)

    def test_concept_date_filter_valid_start(self):
        expr = ConceptDateFilter(valid_start_date="2020-01-01")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("valid_start_date >= '2020-01-01'", sql)

    def test_concept_date_filter_valid_end(self):
        expr = ConceptDateFilter(valid_end_date="2024-12-31")
        sql = self.compiler.compile_expression(expr)
        self.assertIn("valid_end_date <= '2024-12-31'", sql)

    def test_concept_date_filter_with_scope(self):
        scope = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        expr = ConceptDateFilter(valid_on_date="2024-01-01", scope=scope)
        sql = self.compiler.compile_expression(expr)
        self.assertIn("vocabulary_id = 'SNOMED'", sql)
        self.assertIn("domain_id = 'Condition'", sql)
        self.assertIn("valid_start_date <= '2024-01-01'", sql)
