"""
Test JSON interoperability between Java and Python implementations.

This module tests that the Python implementation can handle JSON generated
by the Java version and vice versa.
"""

import json
import unittest
from typing import Dict, Any

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from circe.cohortdefinition.criteria import ConditionOccurrence
from circe.vocabulary.concept import Concept


class TestJavaInteroperability(unittest.TestCase):
    """Test Java-Python JSON interoperability."""
    
    def test_java_json_with_null_gender_concept_id(self):
        """Test handling JSON from Java with null concept_id values."""
        # This is the kind of JSON that Java might generate
        java_json = {
            "codesetId": 123,
            "first": True,
            "gender": [
                {
                    "conceptId": None,  # Java allows null
                    "conceptName": "Unknown",
                    "conceptCode": None
                }
            ],
            "age": {
                "minValue": 18,
                "maxValue": 65
            }
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
            "age": {
                "minValue": 18,
                "maxValue": 65
            }
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
            "age": {
                "minValue": 18,
                "maxValue": 65
            }
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
            gender=[Concept(concept_id=None, concept_name="Unknown")],
            age={"min_value": 18, "max_value": 65}
        )
        
        # Convert to JSON
        json_data = criteria.model_dump(by_alias=True)
        
        # Should contain the expected structure
        self.assertEqual(json_data["codesetId"], 123)
        self.assertTrue(json_data["first"])
        self.assertIsNotNone(json_data["gender"])
        self.assertEqual(len(json_data["gender"]), 1)
        self.assertIsNone(json_data["gender"][0]["conceptId"])
        self.assertEqual(json_data["gender"][0]["conceptName"], "Unknown")
        
        # Should be able to parse it back
        criteria_roundtrip = ConditionOccurrence.model_validate(json_data)
        self.assertEqual(criteria_roundtrip.codeset_id, 123)
        self.assertTrue(criteria_roundtrip.first)
        self.assertIsNotNone(criteria_roundtrip.gender)
        self.assertEqual(len(criteria_roundtrip.gender), 1)
        self.assertIsNone(criteria_roundtrip.gender[0].concept_id)
    
    def test_java_json_with_mixed_valid_invalid_concepts(self):
        """Test handling JSON with mix of valid and invalid concept IDs."""
        java_json = {
            "codesetId": 123,
            "gender": [
                {
                    "conceptId": 8507,  # Valid concept ID (Male)
                    "conceptName": "Male"
                },
                {
                    "conceptId": None,  # Invalid concept ID
                    "conceptName": "Unknown"
                },
                {
                    "conceptId": 8532,  # Valid concept ID (Female)
                    "conceptName": "Female"
                }
            ]
        }
        
        # Python should be able to parse this JSON
        criteria = ConditionOccurrence.model_validate(java_json)
        
        # Should handle mixed valid/invalid concept IDs
        self.assertIsNotNone(criteria.gender)
        self.assertEqual(len(criteria.gender), 3)
        self.assertEqual(criteria.gender[0].concept_id, 8507)
        self.assertIsNone(criteria.gender[1].concept_id)
        self.assertEqual(criteria.gender[2].concept_id, 8532)


if __name__ == '__main__':
    unittest.main()
