"""
Test Concept Set Schema Compatibility

Tests that the implementation supports both legacy and new OHDSI concept set schemas.
"""

import json
import unittest
from pathlib import Path

from circe.vocabulary.concept import (
    Concept,
    ConceptExpressionItem,
    ConceptSet,
    ConceptSetExpression,
    ConceptSetItem,  # Backward compatibility alias
)
from circe.vocabulary.concept_set_expression_query_builder import (
    ConceptSetExpressionQueryBuilder,
)


class TestConceptSetSchemaCompatibility(unittest.TestCase):
    """Test compatibility with both legacy and new concept set schemas."""

    @classmethod
    def setUpClass(cls):
        """Load test fixtures."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "schemas"

        with open(fixtures_dir / "concept_set_legacy.json") as f:
            cls.legacy_data = json.load(f)

        with open(fixtures_dir / "concept_set_new_schema.json") as f:
            cls.new_schema_data = json.load(f)

    def test_legacy_concept_set_loads(self):
        """Test that legacy concept set JSON loads correctly."""
        concept_set = ConceptSet.model_validate(self.legacy_data)

        self.assertEqual(concept_set.id, 1)
        self.assertEqual(concept_set.name, "Type 2 Diabetes Mellitus")
        self.assertIsNotNone(concept_set.expression)
        self.assertEqual(len(concept_set.expression.items), 2)

        # Legacy format doesn't have new fields
        self.assertIsNone(concept_set.version)
        self.assertIsNone(concept_set.created_by_tool)
        self.assertIsNone(concept_set.tags)

    def test_new_schema_concept_set_loads(self):
        """Test that new schema concept set JSON loads correctly."""
        concept_set = ConceptSet.model_validate(self.new_schema_data)

        self.assertEqual(concept_set.id, 2)
        self.assertEqual(concept_set.name, "Hypertension Concept Set")
        self.assertEqual(
            concept_set.description,
            "Comprehensive concept set for essential hypertension including all subtypes",
        )
        self.assertEqual(concept_set.version, "1.0.0")
        self.assertEqual(concept_set.created_by, "researcher@ohdsi.org")
        self.assertEqual(concept_set.created_by_tool, "circe-python 0.1.0")
        self.assertEqual(concept_set.modified_by_tool, "ATLAS 2.14.0")
        self.assertIsNotNone(concept_set.created_date)
        self.assertIsNotNone(concept_set.modified_date)
        self.assertEqual(concept_set.tags, ["hypertension", "cardiovascular", "validated"])
        self.assertIsNotNone(concept_set.metadata)
        self.assertEqual(concept_set.metadata["reviewStatus"], "approved")

    def test_legacy_include_mapped_defaults_to_false(self):
        """Test that legacy items without includeMapped get default value False."""
        # Create legacy format without includeMapped
        legacy_without_mapped = {
            "id": 3,
            "name": "Test",
            "expression": {
                "items": [
                    {
                        "concept": {"conceptId": 123},
                        "isExcluded": False,
                        "includeDescendants": True,
                        # includeMapped is missing - should default to False
                    }
                ]
            },
        }

        concept_set = ConceptSet.model_validate(legacy_without_mapped)
        item = concept_set.expression.items[0]

        # Should default to False for backward compatibility
        self.assertFalse(item.include_mapped)

    def test_new_schema_include_mapped_required(self):
        """Test that new schema properly handles includeMapped field."""
        concept_set = ConceptSet.model_validate(self.new_schema_data)

        # First item has includeMapped=True
        self.assertTrue(concept_set.expression.items[0].include_mapped)
        # Second item has includeMapped=False
        self.assertFalse(concept_set.expression.items[1].include_mapped)

    def test_concept_validation_new_fields(self):
        """Test that Concept supports new schema fields."""
        concept_data = {
            "conceptId": 320128,
            "conceptName": "Essential hypertension",
            "domainId": "Condition",
            "vocabularyId": "SNOMED",
            "conceptClassId": "Clinical Finding",
            "standardConcept": "S",
            "conceptCode": "59621000",
            "validStartDate": "1970-01-01",
            "validEndDate": "2099-12-31",
            "invalidReason": None,
        }

        concept = Concept.model_validate(concept_data)

        self.assertEqual(concept.concept_id, 320128)
        self.assertEqual(concept.valid_start_date, "1970-01-01")
        self.assertEqual(concept.valid_end_date, "2099-12-31")
        self.assertIsNone(concept.invalid_reason)

    def test_concept_standard_concept_validation(self):
        """Test that standardConcept accepts various values for backward compatibility."""
        # Common valid values
        for value in ["S", "C", None]:
            concept = Concept(concept_id=1, standard_concept=value)
            self.assertEqual(concept.standard_concept, value)

        # Legacy data may have other values - should be accepted for compatibility
        concept = Concept(concept_id=1, standard_concept="X")
        self.assertEqual(concept.standard_concept, "X")

    def test_concept_invalid_reason_validation(self):
        """Test that invalidReason accepts various values for backward compatibility."""
        # Common valid values
        for value in ["D", "U", None]:
            concept = Concept(concept_id=1, invalid_reason=value)
            self.assertEqual(concept.invalid_reason, value)

        # Legacy data may have values like 'V' - should be accepted for compatibility
        concept = Concept(concept_id=1, invalid_reason="V")
        self.assertEqual(concept.invalid_reason, "V")

    def test_version_semantic_validation(self):
        """Test that version field accepts semantic versioning and other formats for compatibility."""
        # Semantic versioning formats
        for version in ["1.0.0", "2.14.3", "0.1.0"]:
            cs = ConceptSet(id=1, name="Test", expression=ConceptSetExpression(items=[]), version=version)
            self.assertEqual(cs.version, version)

        # Legacy data may have other version formats - should be accepted for compatibility
        for version in ["1.0", "v1.0.0", "1.0.0-alpha"]:
            cs = ConceptSet(id=1, name="Test", expression=ConceptSetExpression(items=[]), version=version)
            self.assertEqual(cs.version, version)

    def test_concept_expression_item_backward_compatibility(self):
        """Test that ConceptSetItem alias still works."""
        # ConceptSetItem should be an alias for ConceptExpressionItem
        self.assertIs(ConceptSetItem, ConceptExpressionItem)

        # Both should work
        item1 = ConceptExpressionItem(
            concept=Concept(concept_id=1), is_excluded=False, include_descendants=True, include_mapped=False
        )

        item2 = ConceptSetItem(
            concept=Concept(concept_id=1), is_excluded=False, include_descendants=True, include_mapped=False
        )

        self.assertEqual(type(item1), type(item2))

    def test_query_builder_works_with_both_schemas(self):
        """Test that ConceptSetExpressionQueryBuilder works with both schema versions."""
        builder = ConceptSetExpressionQueryBuilder()

        # Test with legacy schema
        legacy_cs = ConceptSet.model_validate(self.legacy_data)
        legacy_query = builder.build_expression_query(legacy_cs.expression)
        self.assertIn("select distinct I.concept_id", legacy_query)
        self.assertIn("FROM", legacy_query)

        # Test with new schema
        new_cs = ConceptSet.model_validate(self.new_schema_data)
        new_query = builder.build_expression_query(new_cs.expression)
        self.assertIn("select distinct I.concept_id", new_query)
        self.assertIn("FROM", new_query)

        # New schema has includeMapped=True for first item, should include mapping logic
        self.assertIn("Maps to", new_query)

    def test_query_builder_handles_include_mapped(self):
        """Test that query builder properly handles includeMapped flag."""
        builder = ConceptSetExpressionQueryBuilder()

        # Create expression with includeMapped=True
        expression = ConceptSetExpression(
            items=[
                ConceptExpressionItem(
                    concept=Concept(concept_id=320128),
                    is_excluded=False,
                    include_descendants=False,
                    include_mapped=True,  # This should trigger mapping logic
                )
            ]
        )

        query = builder.build_expression_query(expression)

        # Should include concept_relationship join for mapping
        self.assertIn("concept_relationship", query)
        self.assertIn("Maps to", query)

    def test_serialization_preserves_field_names(self):
        """Test that serialization uses correct field names for new schema."""
        concept_set = ConceptSet.model_validate(self.new_schema_data)

        # Serialize back to dict
        serialized = concept_set.model_dump(by_alias=True, exclude_none=True)

        # Check that camelCase is preserved
        self.assertIn("createdByTool", serialized)
        self.assertIn("modifiedByTool", serialized)
        self.assertIn("createdDate", serialized)
        self.assertIn("modifiedDate", serialized)

    def test_empty_expression_allowed_for_legacy_compatibility(self):
        """Test that empty expression items are allowed for legacy compatibility."""
        cs = ConceptSet(id=1, name="Test", expression=ConceptSetExpression(items=[]))

        self.assertEqual(len(cs.expression.items), 0)

    def test_max_length_validations(self):
        """Test that max length validations are enforced."""
        # name max 255 characters
        with self.assertRaises(ValueError):
            ConceptSet(id=1, name="x" * 256, expression=ConceptSetExpression(items=[]))

        # description max 4000 characters
        with self.assertRaises(ValueError):
            ConceptSet(id=1, name="Test", description="x" * 4001, expression=ConceptSetExpression(items=[]))

    def test_tags_validation(self):
        """Test that tags are validated properly."""
        # Valid tags
        cs = ConceptSet(
            id=1,
            name="Test",
            expression=ConceptSetExpression(items=[]),
            tags=["tag1", "tag2", "x" * 100],  # Max 100 chars per tag
        )
        self.assertEqual(len(cs.tags), 3)

        # Tag too long
        with self.assertRaises(ValueError):
            ConceptSet(id=1, name="Test", expression=ConceptSetExpression(items=[]), tags=["x" * 101])

        # Empty tag
        with self.assertRaises(ValueError):
            ConceptSet(id=1, name="Test", expression=ConceptSetExpression(items=[]), tags=[""])


if __name__ == "__main__":
    unittest.main()
