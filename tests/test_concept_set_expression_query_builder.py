import unittest
from unittest.mock import MagicMock
from circe.vocabulary.concept_set_expression_query_builder import ConceptSetExpressionQueryBuilder
from circe.vocabulary.concept import Concept
from circe.vocabulary.concept import ConceptSetExpression, ConceptSetItem

class TestConceptSetExpressionQueryBuilder(unittest.TestCase):

    def setUp(self):
        self.builder = ConceptSetExpressionQueryBuilder()

    def test_get_concept_ids(self):
        c1 = Concept(concept_id=1, concept_name="C1")
        c2 = Concept(concept_id=2, concept_name="C2")
        c3 = Concept(concept_id=None, concept_name="C3") # Should be ignored
        ids = self.builder.get_concept_ids([c1, c2, c3])
        self.assertEqual(ids, [1, 2])

    def test_build_concept_set_sub_query_basic(self):
        c1 = Concept(concept_id=1, concept_name="C1")
        query = self.builder.build_concept_set_sub_query([c1], [])
        self.assertIn("select concept_id", query)
        self.assertIn("from @vocabulary_database_schema.CONCEPT", query)
        self.assertIn("where (concept_id in (1))", query)

    def test_build_concept_set_sub_query_descendants(self):
        c1 = Concept(concept_id=1, concept_name="C1")
        query = self.builder.build_concept_set_sub_query([], [c1])
        # Aligned with Java logic: joins concept + concept_ancestor
        self.assertIn("select c.concept_id", query)
        self.assertIn("from @vocabulary_database_schema.CONCEPT c", query)
        self.assertIn("join @vocabulary_database_schema.CONCEPT_ANCESTOR ca", query)
        self.assertIn("and (ca.ancestor_concept_id in (1))", query)

    def test_build_concept_set_sub_query_mixed(self):
        c1 = Concept(concept_id=1, concept_name="C1")
        c2 = Concept(concept_id=2, concept_name="C2")
        query = self.builder.build_concept_set_sub_query([c1], [c2])
        self.assertIn("select concept_id", query)
        self.assertIn("UNION", query)
        # Check for descendants part
        self.assertIn("join @vocabulary_database_schema.CONCEPT_ANCESTOR ca", query)

    def test_build_concept_set_mapped_query(self):
        c1 = Concept(concept_id=1, concept_name="C1")
        query = self.builder.build_concept_set_mapped_query([c1], [])
        self.assertIn("join @vocabulary_database_schema.concept_relationship cr", query)
        # Condition is now in ON clause, not WHERE
        self.assertIn("cr.relationship_id = 'Maps to'", query)

    def test_build_concept_set_query_empty(self):
        query = self.builder.build_concept_set_query([], [], [], [])
        self.assertIn("select concept_id from @vocabulary_database_schema.CONCEPT where 0=1", query)

    def test_build_concept_set_query_with_mapping(self):
        c1 = Concept(concept_id=1, concept_name="C1")
        query = self.builder.build_concept_set_query([c1], [], [c1], [])
        self.assertIn("UNION", query)
        self.assertIn("Maps to", query)

    def test_build_expression_query_simple_include(self):
        c1 = Concept(concept_id=1, concept_name="C1")
        item = ConceptSetItem(concept=c1, is_excluded=False, include_descendants=False, include_mapped=False)
        expression = ConceptSetExpression(items=[item])
        
        query = self.builder.build_expression_query(expression)
        
        # Java uses lowercase select distinct
        self.assertIn("select distinct I.concept_id", query)
        self.assertIn("FROM", query)
        # Should not have exclusion join
        self.assertNotIn("LEFT JOIN", query)
        self.assertNotIn("E.concept_id is null", query)

    def test_build_expression_query_with_exclude(self):
        c1 = Concept(concept_id=1, concept_name="C1")
        c2 = Concept(concept_id=2, concept_name="C2")
        
        item1 = ConceptSetItem(concept=c1, is_excluded=False, include_descendants=False, include_mapped=False)
        item2 = ConceptSetItem(concept=c2, is_excluded=True, include_descendants=False, include_mapped=False)
        
        expression = ConceptSetExpression(items=[item1, item2])
        
        query = self.builder.build_expression_query(expression)
        
        self.assertIn("select distinct I.concept_id", query)
        self.assertIn("LEFT JOIN", query)
        self.assertIn("E.concept_id is null", query)

    def test_build_expression_query_complex_flags(self):
        """Test combinations of include_descendants and include_mapped."""
        c1 = Concept(concept_id=1, concept_name="C1")
        
        # Test mapped + descendants
        item = ConceptSetItem(concept=c1, is_excluded=False, include_descendants=True, include_mapped=True)
        expression = ConceptSetExpression(items=[item])
        
        query = self.builder.build_expression_query(expression)
        
        # Should have standard concept lookup
        self.assertIn("select concept_id", query)
        # Should have descendants lookup
        self.assertIn("CONCEPT_ANCESTOR", query)
        # Should have mapped lookup
        self.assertIn("concept_relationship", query)

    def test_build_expression_query_complex_exclude(self):
        """Test excluded items with various flags."""
        c1 = Concept(concept_id=1, concept_name="C1")
        
        # Test excluded + mapped + descendants
        item = ConceptSetItem(concept=c1, is_excluded=True, include_descendants=True, include_mapped=True)
        expression = ConceptSetExpression(items=[item])
        
        query = self.builder.build_expression_query(expression)
        
        # Should have exclusion join
        self.assertIn("LEFT JOIN", query)
        # Should include descendants and mapped logic in exclusion
        self.assertIn("CONCEPT_ANCESTOR", query)
        self.assertIn("concept_relationship", query)
