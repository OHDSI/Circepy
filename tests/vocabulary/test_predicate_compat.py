"""Tests for the compatibility layer and manifest generation."""

import unittest

try:
    import duckdb

    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

from circe.vocabulary.concept import (
    Concept,
    ConceptExpressionItem,
    ConceptSetExpression,
)
from circe.vocabulary.predicate_compat import ConceptSetCompat, ManifestGenerator
from circe.vocabulary.predicate_expressions import (
    HierarchyDescend,
    StringFilter,
    VocabularyScope,
)
from circe.vocabulary.predicate_item import ConceptPredicateItem


class TestConceptSetCompat(unittest.TestCase):
    """Test import/export between extended and traditional OHDSI format."""

    def test_from_ohdsi_json(self):
        ohdsi_items = [
            {
                "concept": {"CONCEPT_ID": 201826, "CONCEPT_NAME": "Type 2 diabetes"},
                "isExcluded": False,
                "includeDescendants": True,
                "includeMapped": False,
            },
            {
                "concept": {"CONCEPT_ID": 315295, "CONCEPT_NAME": "Rheumatic HF"},
                "isExcluded": True,
                "includeDescendants": False,
                "includeMapped": False,
            },
        ]
        cs = ConceptSetCompat.from_ohdsi_json(ohdsi_items)
        self.assertEqual(len(cs.items), 2)
        self.assertIsInstance(cs.items[0], ConceptExpressionItem)
        self.assertEqual(cs.items[0].concept.concept_id, 201826)
        self.assertTrue(cs.items[0].include_descendants)
        self.assertTrue(cs.items[1].is_excluded)

    def test_from_ohdsi_json_empty(self):
        cs = ConceptSetCompat.from_ohdsi_json([])
        self.assertEqual(cs.items, [])

    def test_is_traditional_true(self):
        items = [
            ConceptExpressionItem(concept=Concept(concept_id=1)),
        ]
        cs = ConceptSetExpression(items=items)
        self.assertTrue(ConceptSetCompat.is_traditional(cs))

    def test_is_traditional_false(self):
        items = [
            ConceptPredicateItem(
                expression=VocabularyScope(vocabulary_id="SNOMED"),
            ),
        ]
        cs = ConceptSetExpression(items=items)
        self.assertFalse(ConceptSetCompat.is_traditional(cs))

    def test_is_traditional_empty(self):
        cs = ConceptSetExpression(items=[])
        self.assertTrue(ConceptSetCompat.is_traditional(cs))

    def test_is_traditional_mixed(self):
        items = [
            ConceptExpressionItem(concept=Concept(concept_id=1)),
            ConceptPredicateItem(
                expression=VocabularyScope(vocabulary_id="SNOMED"),
            ),
        ]
        cs = ConceptSetExpression(items=items)
        self.assertFalse(ConceptSetCompat.is_traditional(cs))


@unittest.skipIf(not HAS_DUCKDB, "duckdb not installed")
class TestManifestGenerator(unittest.TestCase):
    """Test resolution manifest generation."""

    @classmethod
    def setUpClass(cls):
        import duckdb

        from circe.vocabulary.predicate_resolver import ConceptSetResolver
        from circe.vocabulary.predicate_sql_compiler import PredicateSQLCompiler

        cls.conn = duckdb.connect(":memory:")
        cls.compiler = PredicateSQLCompiler()

        cls.conn.execute("CREATE SCHEMA IF NOT EXISTS vocab")
        cls.conn.execute("""
            CREATE TABLE vocab.concept (
                concept_id INTEGER, concept_name VARCHAR, domain_id VARCHAR,
                vocabulary_id VARCHAR, concept_class_id VARCHAR,
                standard_concept VARCHAR, concept_code VARCHAR,
                invalid_reason VARCHAR
            )
        """)
        cls.conn.execute("""
            CREATE TABLE vocab.concept_ancestor (
                ancestor_concept_id INTEGER, descendant_concept_id INTEGER,
                min_levels_of_separation INTEGER, max_levels_of_separation INTEGER
            )
        """)
        cls.conn.execute(
            "INSERT INTO vocab.concept VALUES (201820, 'T2DM', 'Condition', 'SNOMED', "
            "'Clinical Finding', 'S', '44054006', NULL)"
        )
        cls.conn.execute(
            "INSERT INTO vocab.concept VALUES (316139, 'Heart failure', 'Condition', 'SNOMED', "
            "'Clinical Finding', 'S', '84114007', NULL)"
        )
        cls.conn.execute(
            "INSERT INTO vocab.concept_ancestor VALUES (201820, 201820, 0, 0)"
        )
        cls.conn.execute(
            "INSERT INTO vocab.concept_ancestor VALUES (316139, 316139, 0, 0)"
        )

        class DuckDBConnection:
            def __init__(self, conn):
                self.conn = conn

            def execute(self, sql):
                return self.conn.execute(
                    sql.replace("@vocabulary_database_schema", "vocab")
                ).fetchall()

        cls.db = DuckDBConnection(cls.conn)
        cls.resolver = ConceptSetResolver(cls.db, cls.compiler)
        cls.gen = ManifestGenerator(cls.compiler)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_manifest_generation(self):
        cs = ConceptSetExpression(
            items=[
                ConceptPredicateItem(
                    expression=VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition"),
                    isExcluded=False,
                )
            ]
        )
        manifest = self.gen.generate(cs, self.resolver, vocabulary_version="v5.0 24-Feb-2025")
        self.assertGreater(manifest.total_concept_count, 0)
        self.assertEqual(manifest.vocabulary_version, "v5.0 24-Feb-2025")
        self.assertEqual(len(manifest.items_resolved), 1)
        self.assertEqual(len(manifest.concept_ids_hash), 64)  # SHA-256 hex
        self.assertEqual(manifest.items_resolved[0].item_type, "concept_predicate_item")

    def test_manifest_deterministic_hash(self):
        cs = ConceptSetExpression(
            items=[
                ConceptPredicateItem(
                    expression=VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition"),
                    isExcluded=False,
                )
            ]
        )
        m1 = self.gen.generate(cs, self.resolver)
        m2 = self.gen.generate(cs, self.resolver)
        self.assertEqual(m1.concept_ids_hash, m2.concept_ids_hash)

    def test_manifest_includes_sql(self):
        cs = ConceptSetExpression(
            items=[
                ConceptPredicateItem(
                    expression=HierarchyDescend(ancestor_concept_id=201820),
                    isExcluded=False,
                )
            ]
        )
        manifest = self.gen.generate(cs, self.resolver)
        self.assertIsNotNone(manifest.items_resolved[0].compiled_sql)
        self.assertIn("CONCEPT_ANCESTOR", manifest.items_resolved[0].compiled_sql)
