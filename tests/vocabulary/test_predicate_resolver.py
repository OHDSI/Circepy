"""Integration tests for the predicate resolver using DuckDB."""

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
from circe.vocabulary.predicate_expressions import (
    HierarchyDescend,
    SetOperation,
    SetOperationNode,
    StringFilter,
    VocabularyScope,
)
from circe.vocabulary.predicate_item import ConceptPredicateItem
from circe.vocabulary.predicate_resolver import ConceptSetResolver
from circe.vocabulary.predicate_sql_compiler import PredicateSQLCompiler


def create_test_vocab(conn):
    """Seed a DuckDB in-memory database with a minimal OMOP vocabulary."""
    conn.execute("CREATE SCHEMA IF NOT EXISTS vocab")
    conn.execute("""
        CREATE TABLE vocab.concept (
            concept_id INTEGER,
            concept_name VARCHAR,
            domain_id VARCHAR,
            vocabulary_id VARCHAR,
            concept_class_id VARCHAR,
            standard_concept VARCHAR,
            concept_code VARCHAR,
            invalid_reason VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE vocab.concept_ancestor (
            ancestor_concept_id INTEGER,
            descendant_concept_id INTEGER,
            min_levels_of_separation INTEGER,
            max_levels_of_separation INTEGER
        )
    """)

    concepts = [
        # Diabetes concepts (SNOMED, Condition)
        (
            201820,
            "Type 2 diabetes mellitus",
            "Condition",
            "SNOMED",
            "Clinical Finding",
            "S",
            "44054006",
            None,
        ),
        (
            443238,
            "Type 1 diabetes mellitus",
            "Condition",
            "SNOMED",
            "Clinical Finding",
            "S",
            "46635009",
            None,
        ),
        (193323, "Diabetic ketoacidosis", "Condition", "SNOMED", "Clinical Finding", "S", "397774000", None),
        (
            40484648,
            "Diabetes mellitus in pregnancy",
            "Condition",
            "SNOMED",
            "Clinical Finding",
            "S",
            "1168702002",
            None,
        ),
        (
            4058243,
            "Gestational diabetes mellitus",
            "Condition",
            "SNOMED",
            "Clinical Finding",
            "S",
            "1168702002",
            None,
        ),
        # Heart failure concepts (SNOMED, Condition)
        (316139, "Heart failure", "Condition", "SNOMED", "Clinical Finding", "S", "84114007", None),
        (
            315295,
            "Congestive rheumatic heart failure",
            "Condition",
            "SNOMED",
            "Clinical Finding",
            "S",
            "82523003",
            None,
        ),
        # Non-condition concepts that should be excluded by domain filter
        (19067763, "Metformin", "Drug", "RxNorm", "Ingredient", "S", "6809", None),
        (21600712, "Insulin glargine", "Drug", "RxNorm", "Ingredient", "S", "284387", None),
    ]
    for c in concepts:
        conn.execute("INSERT INTO vocab.concept VALUES (?, ?, ?, ?, ?, ?, ?, ?)", c)

    # Ancestor relationships: 201820 (T2DM) -> children
    ancestors = [
        (201820, 201820, 0, 0),  # self
        (201820, 443238, 1, 1),  # Type 1 (invalid real-world but fine for test)
        (201820, 193323, 1, 1),  # DKA
        (201820, 40484648, 1, 1),  # Diabetes in pregnancy
        (201820, 4058243, 1, 1),  # Gestational
        (4058243, 4058243, 0, 0),  # self
        (316139, 316139, 0, 0),  # self
        (315295, 315295, 0, 0),  # self
    ]
    for a in ancestors:
        conn.execute("INSERT INTO vocab.concept_ancestor VALUES (?, ?, ?, ?)", a)


@unittest.skipIf(not HAS_DUCKDB, "duckdb not installed")
class TestConceptSetResolverIntegration(unittest.TestCase):
    """Integration tests with DuckDB in-memory vocabulary."""

    @classmethod
    def setUpClass(cls):
        cls.conn = duckdb.connect(":memory:")
        cls.compiler = PredicateSQLCompiler()
        create_test_vocab(cls.conn)

        class DuckDBConnection:
            def __init__(self, conn):
                self.conn = conn

            def execute(self, sql: str) -> list[tuple]:
                sql_clean = sql.replace("@vocabulary_database_schema", "vocab")
                return self.conn.execute(sql_clean).fetchall()

        cls.db = DuckDBConnection(cls.conn)
        cls.resolver = ConceptSetResolver(cls.db, cls.compiler)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_resolve_vocabulary_scope(self):
        expr = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        result = self.resolver.resolve_expression(expr)
        self.assertGreater(len(result), 0)
        self.assertIn(201820, result)
        self.assertIn(316139, result)
        self.assertNotIn(19067763, result)

    def test_resolve_hierarchy_descend(self):
        expr = HierarchyDescend(ancestor_concept_id=201820)
        result = self.resolver.resolve_expression(expr)
        self.assertIn(201820, result)  # ancestor is included by default
        self.assertIn(443238, result)
        self.assertIn(193323, result)

    def test_resolve_hierarchy_descend_exclude_ancestor(self):
        expr = HierarchyDescend(ancestor_concept_id=201820, include_ancestor=False)
        result = self.resolver.resolve_expression(expr)
        self.assertNotIn(201820, result)
        self.assertIn(443238, result)

    def test_resolve_hierarchy_descend_max_depth(self):
        expr = HierarchyDescend(ancestor_concept_id=201820, max_depth=0)
        result = self.resolver.resolve_expression(expr)
        self.assertEqual(result, {201820})

    def test_resolve_string_filter(self):
        expr = StringFilter(pattern="%diabetes%")
        result = self.resolver.resolve_expression(expr)
        self.assertIn(201820, result)
        self.assertIn(443238, result)

    def test_resolve_string_filter_with_scope(self):
        scope = VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition")
        expr = StringFilter(pattern="%heart%", scope=scope)
        result = self.resolver.resolve_expression(expr)
        self.assertIn(316139, result)
        self.assertIn(315295, result)

    def test_resolve_set_union(self):
        t2dm = HierarchyDescend(ancestor_concept_id=201820)
        hf = HierarchyDescend(ancestor_concept_id=316139)
        expr = SetOperationNode(operation=SetOperation.UNION, operands=[t2dm, hf])
        result = self.resolver.resolve_expression(expr)
        self.assertIn(201820, result)
        self.assertIn(316139, result)

    def test_resolve_set_minus(self):
        diabetes = HierarchyDescend(ancestor_concept_id=201820)
        gestational = HierarchyDescend(ancestor_concept_id=4058243)
        expr = SetOperationNode(operation=SetOperation.MINUS, operands=[diabetes, gestational])
        result = self.resolver.resolve_expression(expr)
        self.assertIn(201820, result)
        self.assertNotIn(4058243, result)

    def test_resolve_set_intersect(self):
        diabetes = HierarchyDescend(ancestor_concept_id=201820, include_ancestor=False)
        expr = StringFilter(pattern="%diabetes%")
        intersect = SetOperationNode(operation=SetOperation.INTERSECT, operands=[diabetes, expr])
        result = self.resolver.resolve_expression(intersect)
        # Only concepts that are both diabetes descendants AND have 'diabetes' in name
        for c in result:
            name = self.conn.execute(
                "SELECT concept_name FROM vocab.concept WHERE concept_id = ?", (c,)
            ).fetchone()[0]
            self.assertIn("diabetes", name.lower())

    def test_resolve_mixed_concept_set(self):
        """Traditional item + predicate item together."""
        traditional = ConceptExpressionItem(
            concept=Concept(concept_id=316139, concept_name="Heart failure"),
            isExcluded=False,
        )
        predicate = ConceptPredicateItem(
            expression=StringFilter(pattern="%diabetes%"),
            isExcluded=False,
        )
        cs = ConceptSetExpression(items=[traditional, predicate])
        result = self.resolver.resolve(cs)
        self.assertIn(316139, result)
        self.assertIn(201820, result)

    def test_resolve_mixed_with_exclusion(self):
        """Traditional include, predicate exclude."""
        traditional = ConceptExpressionItem(
            concept=Concept(concept_id=201820, concept_name="T2DM"),
            isExcluded=False,
        )
        exclude = ConceptPredicateItem(
            name="Exclude gestational",
            expression=HierarchyDescend(ancestor_concept_id=4058243),
            isExcluded=True,
        )
        cs = ConceptSetExpression(items=[traditional, exclude])
        result = self.resolver.resolve(cs)
        self.assertIn(201820, result)
        self.assertNotIn(4058243, result)

    def test_resolve_traditional_only(self):
        """Pure traditional items resolve correctly."""
        item = ConceptExpressionItem(
            concept=Concept(concept_id=201820, concept_name="T2DM"),
            isExcluded=False,
        )
        cs = ConceptSetExpression(items=[item])
        result = self.resolver.resolve(cs)
        self.assertEqual(result, {201820})

    def test_resolve_empty_items(self):
        cs = ConceptSetExpression(items=[])
        result = self.resolver.resolve(cs)
        self.assertEqual(result, set())

    def test_resolve_predicate_only_excluded(self):
        """All-excluded predicate item yields empty set."""
        item = ConceptPredicateItem(
            expression=VocabularyScope(vocabulary_id="SNOMED", domain_id="Condition"),
            isExcluded=True,
        )
        cs = ConceptSetExpression(items=[item])
        result = self.resolver.resolve(cs)
        self.assertEqual(result, set())
