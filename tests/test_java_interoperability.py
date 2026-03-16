"""
Test JSON interoperability between Java and Python implementations.

This module tests that the Python implementation can handle JSON generated
by the Java version and vice versa.
"""

import json
import os

# Add project root to path for imports
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from circe.cohortdefinition.cohort import CohortExpression
from circe.cohortdefinition.core import NumericRange, ObservationFilter, ResultLimit
from circe.cohortdefinition.criteria import ConditionOccurrence, PrimaryCriteria
from circe.vocabulary.concept import (
    Concept,
    ConceptSet,
    ConceptSetExpression,
    ConceptSetItem,
)


class TestJavaInteroperability(unittest.TestCase):
    """Test Java-Python JSON interoperability."""

    def test_java_json_with_null_gender_concept_id(self):
        """Test handling JSON from Java with null concept_id values."""
        # This is the kind of JSON that Java might generate (using ALL_CAPS for Concept fields)
        java_json = {
            "CodesetId": 123,
            "First": True,
            "gender": [  # Note: lowercase for simple fields
                {
                    "CONCEPT_ID": None,  # Java allows null
                    "CONCEPT_NAME": "Unknown",
                    "CONCEPT_CODE": None,
                }
            ],
            "Age": {"Value": 18, "Extent": 65},
        }

        # Python should be able to parse this JSON
        criteria = ConditionOccurrence.model_validate(java_json)

        # Should handle None concept_id gracefully
        self.assertIsNotNone(criteria.gender)
        self.assertEqual(len(criteria.gender), 1)
        self.assertIsNone(criteria.gender[0].concept_id)
        self.assertEqual(criteria.gender[0].concept_name, "Unknown")

    def test_java_json_with_null_gender_array(self):
        """Test handling JSON from Java with null gender array."""
        java_json = {
            "codesetId": 123,
            "first": True,
            "gender": None,  # Java allows null arrays
            "age": {"minValue": 18, "maxValue": 65},
        }

        # Python should be able to parse this JSON
        criteria = ConditionOccurrence.model_validate(java_json)

        # Should handle None gender gracefully
        self.assertIsNone(criteria.gender)

    def test_java_json_with_empty_gender_array(self):
        """Test handling JSON from Java with empty gender array."""
        java_json = {
            "codesetId": 123,
            "first": True,
            "gender": [],  # Java allows empty arrays
            "age": {"minValue": 18, "maxValue": 65},
        }

        # Python should be able to parse this JSON
        criteria = ConditionOccurrence.model_validate(java_json)

        # Should handle empty array gracefully
        self.assertEqual(criteria.gender, [])

    def test_python_to_java_json_roundtrip(self):
        """Test that Python can generate JSON that Java can consume."""
        # Create Python criteria
        criteria = ConditionOccurrence(
            codeset_id=123,
            first=True,
            gender=[Concept(concept_id=8507, concept_name="Male")],
            age=NumericRange(value=18, extent=65),
        )

        # Convert to JSON (note: polymorphic wrapper is added)
        json_data = criteria.model_dump(by_alias=True, exclude_none=True)

        # Check polymorphic wrapper
        self.assertIn("ConditionOccurrence", json_data)
        inner_data = json_data["ConditionOccurrence"]

        # Should contain the expected structure
        self.assertEqual(inner_data["CodesetId"], 123)
        self.assertTrue(inner_data["First"])  # PascalCase with alias
        self.assertIsNotNone(inner_data["gender"])  # lowercase for simple field
        self.assertEqual(len(inner_data["gender"]), 1)
        self.assertEqual(inner_data["gender"][0]["CONCEPT_ID"], 8507)
        self.assertEqual(inner_data["gender"][0]["CONCEPT_NAME"], "Male")

        # Note: Polymorphic criteria can't be directly deserialized from wrapped format
        # They're meant to be deserialized as part of a CohortExpression structure
        # where the parent handles the polymorphic unwrapping

    def test_java_json_with_mixed_valid_invalid_concepts(self):
        """Test handling JSON with mix of valid and invalid concept IDs."""
        java_json = {
            "CodesetId": 123,
            "gender": [  # Note: lowercase for simple fields
                {
                    "CONCEPT_ID": 8507,  # Valid concept ID (Male)
                    "CONCEPT_NAME": "Male",
                },
                {
                    "CONCEPT_ID": None,  # Invalid concept ID
                    "CONCEPT_NAME": "Unknown",
                },
                {
                    "CONCEPT_ID": 8532,  # Valid concept ID (Female)
                    "CONCEPT_NAME": "Female",
                },
            ],
        }

        # Python should be able to parse this JSON
        criteria = ConditionOccurrence.model_validate(java_json)

        # Should handle mixed valid/invalid concept IDs
        self.assertIsNotNone(criteria.gender)
        self.assertEqual(len(criteria.gender), 3)
        self.assertEqual(criteria.gender[0].concept_id, 8507)
        self.assertIsNone(criteria.gender[1].concept_id)
        self.assertEqual(criteria.gender[2].concept_id, 8532)


class TestJavaExportCompatibility(unittest.TestCase):
    """Test JSON export compatibility with Java format."""

    def test_field_names_use_pascal_case(self):
        """Test that exported JSON uses PascalCase field names like Java."""
        # Create a cohort expression
        cohort = CohortExpression(
            title="Test Cohort",
            concept_sets=[
                ConceptSet(
                    id=1,
                    name="Test Concept Set",
                    expression=ConceptSetExpression(
                        items=[
                            ConceptSetItem(
                                concept=Concept(concept_id=123, concept_name="Test"),
                                is_excluded=False,
                                include_descendants=True,
                                include_mapped=False,
                            )
                        ],
                        is_excluded=False,
                        include_mapped=False,
                        include_descendants=True,
                    ),
                )
            ],
        )

        # Export to JSON
        json_data = cohort.model_dump(by_alias=True, exclude_none=True)

        # Check PascalCase field names (Java format)
        self.assertIn("ConceptSets", json_data)
        self.assertNotIn("conceptSets", json_data)
        self.assertNotIn("concept_sets", json_data)

        concept_set = json_data["ConceptSets"][0]
        self.assertIn("id", concept_set)  # Java uses lowercase
        self.assertIn("name", concept_set)  # Java uses lowercase
        self.assertIn("expression", concept_set)  # Java uses lowercase

        expression = concept_set["expression"]
        self.assertIn("isExcluded", expression)  # Java uses camelCase
        self.assertIn("includeMapped", expression)  # Java uses camelCase
        self.assertIn("includeDescendants", expression)  # Java uses camelCase
        self.assertIn("items", expression)  # Java uses lowercase

        item = expression["items"][0]
        self.assertIn("concept", item)  # Java uses lowercase
        self.assertIn("isExcluded", item)  # Java uses camelCase
        self.assertIn("includeDescendants", item)  # Java uses camelCase
        self.assertIn("includeMapped", item)  # Java uses camelCase

        concept = item["concept"]
        self.assertIn("CONCEPT_ID", concept)  # Java uses ALL_CAPS
        self.assertIn("CONCEPT_NAME", concept)  # Java uses ALL_CAPS

    def test_criteria_polymorphic_wrapper(self):
        """Test that criteria objects are wrapped in type names."""
        # Create a condition occurrence
        condition = ConditionOccurrence(
            codeset_id=6, first=False, condition_type_exclude=False
        )

        # Export to JSON
        json_data = condition.model_dump(by_alias=True, exclude_none=True)

        # Check polymorphic wrapper
        self.assertIn("ConditionOccurrence", json_data)
        inner_data = json_data["ConditionOccurrence"]
        self.assertIn("CodesetId", inner_data)
        self.assertIn("ConditionTypeExclude", inner_data)

    def test_primary_criteria_uses_pascal_case(self):
        """Test PrimaryCriteria exports with PascalCase field names."""

        primary = PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(
                    codeset_id=1, first=True, condition_type_exclude=False
                )
            ],
            observation_window=ObservationFilter(prior_days=365, post_days=1),
            primary_limit=ResultLimit(type="All"),
        )

        json_data = primary.model_dump(by_alias=True, exclude_none=True)

        # Check PascalCase field names
        self.assertIn("CriteriaList", json_data)
        self.assertIn("ObservationWindow", json_data)
        self.assertIn("PrimaryCriteriaLimit", json_data)

        # Check ObservationWindow fields
        obs_window = json_data["ObservationWindow"]
        self.assertIn("PriorDays", obs_window)
        self.assertIn("PostDays", obs_window)

    def test_round_trip_with_java_format(self):
        """Test Python → JSON → Python round trip maintains data."""
        # Create a cohort
        original = CohortExpression(
            title="Test Cohort",
            concept_sets=[
                ConceptSet(
                    id=1,
                    name="Test",
                    expression=ConceptSetExpression(
                        items=[],
                        is_excluded=False,
                        include_mapped=False,
                        include_descendants=True,
                    ),
                )
            ],
        )

        # Export to JSON string (Java format)
        json_str = original.model_dump_json(by_alias=True, exclude_none=True)

        # Import back from JSON
        restored = CohortExpression.model_validate_json(json_str)

        # Check data integrity
        self.assertEqual(restored.title, "Test Cohort")
        self.assertEqual(len(restored.concept_sets), 1)
        self.assertEqual(restored.concept_sets[0].id, 1)
        self.assertEqual(restored.concept_sets[0].name, "Test")

    def test_compare_with_java_json_file(self):
        """Test that Python export matches Java JSON structure."""
        # Load a Java JSON file
        test_dir = Path(__file__).parent
        java_json_path = test_dir / "cohorts" / "22159.json"

        if not java_json_path.exists():
            self.skipTest(f"Java JSON file not found: {java_json_path}")

        with open(java_json_path) as f:
            java_data = json.load(f)

        # Parse with Python
        cohort = CohortExpression.model_validate(java_data)

        # Export back to JSON
        python_data = cohort.model_dump(by_alias=True, exclude_none=True)

        # Check key structure matches
        if "ConceptSets" in java_data:
            self.assertIn("ConceptSets", python_data)
        if "PrimaryCriteria" in java_data:
            self.assertIn("PrimaryCriteria", python_data)
            # Check nested PrimaryCase structure
            java_pc = java_data["PrimaryCriteria"]
            python_pc = python_data["PrimaryCriteria"]
            if "CriteriaList" in java_pc:
                self.assertIn("CriteriaList", python_pc)
            if "ObservationWindow" in java_pc:
                self.assertIn("ObservationWindow", python_pc)


if __name__ == "__main__":
    unittest.main()
