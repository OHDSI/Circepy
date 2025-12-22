"""
Compare python json schema with java version schema

Ensures the Python Pydantic models match the *full nested structure*, types, and required fields
declared in the Java JSON Schema, serving as a 1:1 replacement for the Java version.
"""
import json
import pytest
from deepdiff import DeepDiff  # pip install deepdiff

from circe import get_json_schema

# Path to Java schema JSON
JAVA_SCHEMA_PATH = "java_cohort_expression_schema.json"

def test_compare_python_java_schema():
    # Load Java schema
    with open(JAVA_SCHEMA_PATH, "r") as f:
        java_schema = json.load(f)

    # Generate Python schema from Pydantic
    python_schema = get_json_schema()

    # Compare with DeepDiff for structure differences
    diff = DeepDiff(java_schema, python_schema, ignore_order=True)

    if diff:
        print("\n❌ Schema differences found:")
        print(json.dumps(diff, indent=2, default=str))
        pytest.fail("Python and Java schemas differ")
    else:
        print("\n✅ Python and Java schemas match!")
