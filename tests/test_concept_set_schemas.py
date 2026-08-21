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

        with open(fixtures_dir / "concept_set_simple.json") as f:
            cls.simple_data = json.load(f)

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

        self.assertEqual(concept_set.id, 456)
        self.assertEqual(concept_set.name, "Heart Failure excluding Rheumatic")
        self.assertEqual(
            concept_set.description,
            "Heart failure concept set excluding rheumatic heart failure cases",
        )
        self.assertEqual(concept_set.version, "1.2.0")
        # These fields are not in the new fixture
        self.assertIsNone(concept_set.created_by)
        self.assertIsNone(concept_set.created_by_tool)
        self.assertIsNone(concept_set.modified_by_tool)
        self.assertIsNone(concept_set.created_date)
        self.assertIsNone(concept_set.modified_date)
        self.assertEqual(concept_set.tags, ["cardiology", "heart-failure"])
        self.assertIsNone(concept_set.metadata)

        # Validate the expression has 2 items
        self.assertEqual(len(concept_set.expression.items), 2)

        # First item - included
        item1 = concept_set.expression.items[0]
        self.assertEqual(item1.concept.concept_id, 316139)
        self.assertEqual(item1.concept.concept_name, "Heart failure")
        self.assertFalse(item1.is_excluded)
        self.assertTrue(item1.include_descendants)
        self.assertFalse(item1.include_mapped)

        # Second item - excluded
        item2 = concept_set.expression.items[1]
        self.assertEqual(item2.concept.concept_id, 315295)
        self.assertEqual(item2.concept.concept_name, "Congestive rheumatic heart failure")
        self.assertTrue(item2.is_excluded)
        self.assertTrue(item2.include_descendants)
        self.assertFalse(item2.include_mapped)

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

        # Both items in the new fixture have includeMapped=false
        self.assertFalse(concept_set.expression.items[0].include_mapped)
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

        # New schema has includeMapped=false for all items, so no mapping logic
        # But it should have exclusion logic since item 2 is excluded
        self.assertIn("LEFT JOIN", new_query)
        self.assertIn("E.concept_id is null", new_query)

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

        # Check that fields present in the fixture are preserved
        self.assertIn("id", serialized)
        self.assertIn("name", serialized)
        self.assertIn("description", serialized)
        self.assertIn("version", serialized)
        self.assertIn("tags", serialized)
        self.assertIn("expression", serialized)

        # Check that expression has proper structure
        self.assertIn("items", serialized["expression"])
        self.assertEqual(len(serialized["expression"]["items"]), 2)

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


class TestSimpleConceptSet(unittest.TestCase):
    """Tests specifically for the simple concept set fixture with full metadata."""

    @classmethod
    def setUpClass(cls):
        """Load simple concept set fixture."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "schemas"
        with open(fixtures_dir / "concept_set_simple.json") as f:
            cls.simple_data = json.load(f)

    def test_simple_concept_set_loads_successfully(self):
        """Test that the simple concept set with full metadata loads correctly."""
        concept_set = ConceptSet.model_validate(self.simple_data)

        # Basic fields
        self.assertEqual(concept_set.id, 123)
        self.assertEqual(concept_set.name, "Type 2 Diabetes Mellitus")
        self.assertEqual(
            concept_set.description,
            "Concept set for identifying Type 2 diabetes mellitus cases in observational studies",
        )
        self.assertEqual(concept_set.version, "1.0.0")

    def test_simple_concept_set_audit_fields(self):
        """Test audit fields are properly loaded."""
        concept_set = ConceptSet.model_validate(self.simple_data)

        self.assertEqual(concept_set.created_by, "researcher@example.org")
        self.assertIsNotNone(concept_set.created_date)
        self.assertEqual(concept_set.created_by_tool, "ATLAS 2.12.0")

        # Fields not present in fixture should be None
        self.assertIsNone(concept_set.modified_by)
        self.assertIsNone(concept_set.modified_date)
        self.assertIsNone(concept_set.modified_by_tool)

    def test_simple_concept_set_tags(self):
        """Test that tags are properly loaded."""
        concept_set = ConceptSet.model_validate(self.simple_data)

        self.assertEqual(len(concept_set.tags), 3)
        self.assertIn("diabetes", concept_set.tags)
        self.assertIn("endocrine", concept_set.tags)
        self.assertIn("chronic-disease", concept_set.tags)

    def test_simple_concept_set_single_item(self):
        """Test that the single concept expression item is properly loaded."""
        concept_set = ConceptSet.model_validate(self.simple_data)

        self.assertEqual(len(concept_set.expression.items), 1)

        item = concept_set.expression.items[0]
        self.assertFalse(item.is_excluded)
        self.assertTrue(item.include_descendants)
        self.assertTrue(item.include_mapped)

    def test_simple_concept_set_concept_details(self):
        """Test that all concept details are properly loaded."""
        concept_set = ConceptSet.model_validate(self.simple_data)
        concept = concept_set.expression.items[0].concept

        self.assertEqual(concept.concept_id, 201826)
        self.assertEqual(concept.concept_name, "Type 2 diabetes mellitus")
        self.assertEqual(concept.domain_id, "Condition")
        self.assertEqual(concept.vocabulary_id, "SNOMED")
        self.assertEqual(concept.concept_class_id, "Clinical Finding")
        self.assertEqual(concept.standard_concept, "S")
        self.assertEqual(concept.concept_code, "44054006")
        self.assertEqual(concept.valid_start_date, "1970-01-01")
        self.assertEqual(concept.valid_end_date, "2099-12-31")
        self.assertIsNone(concept.invalid_reason)

    def test_simple_concept_set_query_generation(self):
        """Test that SQL query can be generated from simple concept set."""
        concept_set = ConceptSet.model_validate(self.simple_data)
        builder = ConceptSetExpressionQueryBuilder()

        query = builder.build_expression_query(concept_set.expression)

        # Should have basic structure
        self.assertIn("select distinct I.concept_id", query)
        self.assertIn("FROM", query)

        # Should have concept ID 201826
        self.assertIn("201826", query)

        # Should include descendants (CONCEPT_ANCESTOR join)
        self.assertIn("CONCEPT_ANCESTOR", query)

        # Should include mapped concepts (concept_relationship join)
        self.assertIn("concept_relationship", query)
        self.assertIn("Maps to", query)

        # Should NOT have exclusion logic since isExcluded=false
        self.assertNotIn("LEFT JOIN", query.split("Maps to")[0])  # Check before mapping logic

    def test_simple_concept_set_roundtrip_serialization(self):
        """Test that simple concept set can be serialized and deserialized."""
        # Load and validate
        concept_set = ConceptSet.model_validate(self.simple_data)

        # Serialize back to dict
        serialized = concept_set.model_dump(by_alias=True, exclude_none=True)

        # Re-validate from serialized data
        concept_set2 = ConceptSet.model_validate(serialized)

        # Should match
        self.assertEqual(concept_set.id, concept_set2.id)
        self.assertEqual(concept_set.name, concept_set2.name)
        self.assertEqual(concept_set.version, concept_set2.version)
        self.assertEqual(len(concept_set.expression.items), len(concept_set2.expression.items))
        self.assertEqual(
            concept_set.expression.items[0].concept.concept_id,
            concept_set2.expression.items[0].concept.concept_id,
        )

    def test_simple_concept_set_include_mapped_flag(self):
        """Test that includeMapped=true is properly handled in query building."""
        concept_set = ConceptSet.model_validate(self.simple_data)
        builder = ConceptSetExpressionQueryBuilder()

        # Build query
        query = builder.build_expression_query(concept_set.expression)

        # Verify mapping logic is included
        self.assertIn("concept_relationship", query)
        self.assertIn("cr.relationship_id = 'Maps to'", query)

    def test_simple_concept_set_include_descendants_flag(self):
        """Test that includeDescendants=true is properly handled in query building."""
        concept_set = ConceptSet.model_validate(self.simple_data)
        builder = ConceptSetExpressionQueryBuilder()

        query = builder.build_expression_query(concept_set.expression)

        # Verify descendant logic is included
        self.assertIn("CONCEPT_ANCESTOR", query)
        self.assertIn("ca.ancestor_concept_id", query)

    def test_simple_concept_set_no_metadata_field(self):
        """Test that metadata field is absent (not just null)."""
        concept_set = ConceptSet.model_validate(self.simple_data)

        # metadata field is not in the fixture, should be None
        self.assertIsNone(concept_set.metadata)

    def test_simple_concept_set_created_date_parsing(self):
        """Test that ISO 8601 date string is parsed correctly."""
        concept_set = ConceptSet.model_validate(self.simple_data)

        # Should parse as datetime
        self.assertIsNotNone(concept_set.created_date)

        # Check year at least
        self.assertEqual(concept_set.created_date.year, 2024)
        self.assertEqual(concept_set.created_date.month, 1)
        self.assertEqual(concept_set.created_date.day, 15)

    def test_simple_vs_complex_schema_compatibility(self):
        """Test that simple schema is compatible with query builder used for complex schemas."""
        # Load both fixtures
        fixtures_dir = Path(__file__).parent / "fixtures" / "schemas"
        with open(fixtures_dir / "concept_set_new_schema.json") as f:
            complex_data = json.load(f)

        simple_cs = ConceptSet.model_validate(self.simple_data)
        complex_cs = ConceptSet.model_validate(complex_data)

        builder = ConceptSetExpressionQueryBuilder()

        # Both should generate valid queries
        simple_query = builder.build_expression_query(simple_cs.expression)
        complex_query = builder.build_expression_query(complex_cs.expression)

        # Both should have the basic structure
        self.assertIn("select distinct I.concept_id", simple_query)
        self.assertIn("select distinct I.concept_id", complex_query)

    def test_simple_concept_set_modify_and_reserialize(self):
        """Test that we can modify the simple concept set and reserialize it."""
        concept_set = ConceptSet.model_validate(self.simple_data)

        # Modify some fields
        concept_set.version = "1.1.0"
        concept_set.modified_by = "reviewer@example.org"
        concept_set.modified_by_tool = "circe-python 0.2.0"
        concept_set.tags.append("validated")

        # Serialize
        serialized = concept_set.model_dump(by_alias=True, exclude_none=True)

        # Check modifications are present
        self.assertEqual(serialized["version"], "1.1.0")
        self.assertEqual(serialized["modifiedBy"], "reviewer@example.org")
        self.assertEqual(serialized["modifiedByTool"], "circe-python 0.2.0")
        self.assertIn("validated", serialized["tags"])


class TestMinimalConceptSet(unittest.TestCase):
    """Tests for minimal concept set with only concept IDs (no full concept details)."""

    @classmethod
    def setUpClass(cls):
        """Load minimal concept set fixture."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "schemas"
        with open(fixtures_dir / "concept_set_minimal.json") as f:
            cls.minimal_data = json.load(f)

    def test_minimal_concept_set_loads_successfully(self):
        """Test that minimal concept set with only concept IDs loads correctly."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        self.assertEqual(concept_set.id, 789)
        self.assertEqual(concept_set.name, "Essential Hypertension")
        self.assertEqual(
            concept_set.description, "Minimal concept set using only concept IDs for efficient storage"
        )
        self.assertEqual(concept_set.version, "1.0.0")

    def test_minimal_concept_set_tool_tracking(self):
        """Test that createdByTool is properly loaded."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        self.assertEqual(concept_set.created_by_tool, "CAPR 4.3")
        # These fields are not in the minimal fixture
        self.assertIsNone(concept_set.created_by)
        self.assertIsNone(concept_set.created_date)
        self.assertIsNone(concept_set.modified_by)
        self.assertIsNone(concept_set.modified_date)
        self.assertIsNone(concept_set.modified_by_tool)

    def test_minimal_concept_set_has_two_items(self):
        """Test that minimal concept set has two expression items."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        self.assertEqual(len(concept_set.expression.items), 2)

    def test_minimal_concept_set_first_item_details(self):
        """Test first concept item (320128) with minimal data."""
        concept_set = ConceptSet.model_validate(self.minimal_data)
        item1 = concept_set.expression.items[0]

        # Check flags
        self.assertFalse(item1.is_excluded)
        self.assertTrue(item1.include_descendants)
        self.assertTrue(item1.include_mapped)

        # Check concept - only ID should be present
        self.assertEqual(item1.concept.concept_id, 320128)
        # All other fields should be None (not provided in minimal format)
        self.assertIsNone(item1.concept.concept_name)
        self.assertIsNone(item1.concept.domain_id)
        self.assertIsNone(item1.concept.vocabulary_id)
        self.assertIsNone(item1.concept.concept_class_id)
        self.assertIsNone(item1.concept.standard_concept)
        self.assertIsNone(item1.concept.concept_code)

    def test_minimal_concept_set_second_item_details(self):
        """Test second concept item (437663) with minimal data."""
        concept_set = ConceptSet.model_validate(self.minimal_data)
        item2 = concept_set.expression.items[1]

        # Check flags - note includeMapped is false for this item
        self.assertFalse(item2.is_excluded)
        self.assertTrue(item2.include_descendants)
        self.assertFalse(item2.include_mapped)

        # Check concept - only ID
        self.assertEqual(item2.concept.concept_id, 437663)
        self.assertIsNone(item2.concept.concept_name)

    def test_minimal_concept_set_query_generation(self):
        """Test that SQL query can be generated from minimal concept set."""
        concept_set = ConceptSet.model_validate(self.minimal_data)
        builder = ConceptSetExpressionQueryBuilder()

        query = builder.build_expression_query(concept_set.expression)

        # Should have basic structure
        self.assertIn("select distinct I.concept_id", query)
        self.assertIn("FROM", query)

        # Should include both concept IDs
        self.assertIn("320128", query)
        self.assertIn("437663", query)

        # Should have descendant logic (both items have includeDescendants=true)
        self.assertIn("CONCEPT_ANCESTOR", query)

        # Should have mapping logic (first item has includeMapped=true)
        self.assertIn("concept_relationship", query)
        self.assertIn("Maps to", query)

    def test_minimal_concept_set_mixed_include_mapped_flags(self):
        """Test that mixed includeMapped flags are handled correctly."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        # First item: includeMapped=true
        self.assertTrue(concept_set.expression.items[0].include_mapped)

        # Second item: includeMapped=false
        self.assertFalse(concept_set.expression.items[1].include_mapped)

        # Query should still be generated correctly
        builder = ConceptSetExpressionQueryBuilder()
        query = builder.build_expression_query(concept_set.expression)

        # Should have mapping logic (because at least one item has includeMapped=true)
        self.assertIn("Maps to", query)

    def test_minimal_concept_set_serialization(self):
        """Test that minimal concept set can be serialized."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        # Serialize
        serialized = concept_set.model_dump(by_alias=True, exclude_none=True)

        # Check structure
        self.assertEqual(serialized["id"], 789)
        self.assertEqual(serialized["name"], "Essential Hypertension")
        self.assertEqual(serialized["createdByTool"], "CAPR 4.3")

        # Expression should have items
        self.assertIn("expression", serialized)
        self.assertEqual(len(serialized["expression"]["items"]), 2)

        # Concepts should only have CONCEPT_ID (using uppercase serialization alias)
        concept1 = serialized["expression"]["items"][0]["concept"]
        self.assertEqual(concept1["CONCEPT_ID"], 320128)
        # Other fields should not be present (exclude_none=True)
        self.assertNotIn("CONCEPT_NAME", concept1)

    def test_minimal_concept_set_efficiency_use_case(self):
        """Test that minimal format is suitable for efficient storage (only IDs)."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        # Verify concepts have minimal data
        for item in concept_set.expression.items:
            # Only concept_id should be set
            self.assertIsNotNone(item.concept.concept_id)

            # All descriptive fields should be None (can be resolved from vocabulary)
            self.assertIsNone(item.concept.concept_name)
            self.assertIsNone(item.concept.domain_id)
            self.assertIsNone(item.concept.vocabulary_id)
            self.assertIsNone(item.concept.concept_class_id)
            self.assertIsNone(item.concept.concept_code)

    def test_minimal_concept_set_tags(self):
        """Test that minimal concept set has proper tags."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        self.assertEqual(len(concept_set.tags), 2)
        self.assertIn("hypertension", concept_set.tags)
        self.assertIn("cardiovascular", concept_set.tags)

    def test_minimal_concept_set_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        concept_set1 = ConceptSet.model_validate(self.minimal_data)

        # Serialize
        serialized = concept_set1.model_dump(by_alias=True, exclude_none=True)

        # Deserialize
        concept_set2 = ConceptSet.model_validate(serialized)

        # Compare
        self.assertEqual(concept_set1.id, concept_set2.id)
        self.assertEqual(concept_set1.name, concept_set2.name)
        self.assertEqual(len(concept_set1.expression.items), len(concept_set2.expression.items))

        # Check concept IDs match
        for i in range(len(concept_set1.expression.items)):
            self.assertEqual(
                concept_set1.expression.items[i].concept.concept_id,
                concept_set2.expression.items[i].concept.concept_id,
            )

    def test_minimal_vs_full_concept_compatibility(self):
        """Test that minimal concepts work with same query builder as full concepts."""
        # Load both minimal and simple (full) fixtures
        fixtures_dir = Path(__file__).parent / "fixtures" / "schemas"
        with open(fixtures_dir / "concept_set_simple.json") as f:
            simple_data = json.load(f)

        minimal_cs = ConceptSet.model_validate(self.minimal_data)
        simple_cs = ConceptSet.model_validate(simple_data)

        builder = ConceptSetExpressionQueryBuilder()

        # Both should generate valid queries
        minimal_query = builder.build_expression_query(minimal_cs.expression)
        simple_query = builder.build_expression_query(simple_cs.expression)

        # Both should have basic structure
        self.assertIn("select distinct I.concept_id", minimal_query)
        self.assertIn("select distinct I.concept_id", simple_query)

        # Both should work despite different levels of concept detail
        self.assertIsNotNone(minimal_query)
        self.assertIsNotNone(simple_query)

    def test_minimal_concept_set_missing_metadata(self):
        """Test that optional metadata field is properly absent."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        self.assertIsNone(concept_set.metadata)
        self.assertIsNone(concept_set.created_by)
        self.assertIsNone(concept_set.created_date)

    def test_minimal_concept_set_can_be_enriched(self):
        """Test that minimal concept set can be enriched with additional data."""
        concept_set = ConceptSet.model_validate(self.minimal_data)

        # Add concept details (simulating vocabulary lookup)
        concept_set.expression.items[0].concept.concept_name = "Essential hypertension"
        concept_set.expression.items[0].concept.domain_id = "Condition"
        concept_set.expression.items[0].concept.vocabulary_id = "SNOMED"

        # Verify enrichment
        self.assertEqual(concept_set.expression.items[0].concept.concept_name, "Essential hypertension")
        self.assertEqual(concept_set.expression.items[0].concept.domain_id, "Condition")

        # Original concept ID should still be there
        self.assertEqual(concept_set.expression.items[0].concept.concept_id, 320128)

    def test_minimal_concept_set_query_with_both_flags(self):
        """Test query generation with both include flags set differently."""
        concept_set = ConceptSet.model_validate(self.minimal_data)
        builder = ConceptSetExpressionQueryBuilder()

        query = builder.build_expression_query(concept_set.expression)

        # First concept (320128): includeDescendants=true, includeMapped=true
        # Should generate:
        # - Direct concept lookup
        # - Descendant lookup via CONCEPT_ANCESTOR
        # - Mapped concept lookup via concept_relationship

        # Second concept (437663): includeDescendants=true, includeMapped=false
        # Should generate:
        # - Direct concept lookup
        # - Descendant lookup via CONCEPT_ANCESTOR
        # - NO mapped concept lookup

        # Overall query should have both types of joins
        self.assertIn("CONCEPT_ANCESTOR", query)
        self.assertIn("concept_relationship", query)


if __name__ == "__main__":
    unittest.main()
