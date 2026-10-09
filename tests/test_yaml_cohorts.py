"""Tests for YAML cohort support with snake_case naming."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from circe.api import build_cohort_query, cohort_expression_from_json, cohort_expression_from_yaml
from circe.cohortdefinition import BuildExpressionQueryOptions
from circe.cohortdefinition.yaml_utils import (
    cohort_expression_to_snake_case,
    dict_to_pascal_case,
    dict_to_snake_case,
    snake_case_dict_to_cohort_expression,
    to_pascal_case,
    to_snake_case,
)
from circe.io import load_expression, save_expression_as_yaml


class TestCaseConversion:
    """Test case conversion utilities."""

    def test_to_snake_case_pascal_case(self):
        """Test converting PascalCase to snake_case."""
        assert to_snake_case("PrimaryCriteria") == "primary_criteria"
        assert to_snake_case("ConceptSets") == "concept_sets"
        assert to_snake_case("CodesetId") == "codeset_id"
        assert to_snake_case("CohortExpression") == "cohort_expression"

    def test_to_snake_case_camel_case(self):
        """Test converting camelCase to snake_case."""
        assert to_snake_case("primaryCriteria") == "primary_criteria"
        assert to_snake_case("conceptSets") == "concept_sets"
        assert to_snake_case("codesetId") == "codeset_id"

    def test_to_snake_case_with_numbers(self):
        """Test converting with numbers."""
        assert to_snake_case("CodesetId") == "codeset_id"
        assert to_snake_case("Concept1Id") == "concept1_id"

    def test_to_snake_case_all_caps(self):
        """Test converting ALL_CAPS and ID suffixes."""
        # CONCEPT_ID already has underscores, just gets lowercased
        assert to_snake_case("CONCEPT_ID") == "concept_id"
        # ConceptID gets underscores before capitals and lowercased
        assert to_snake_case("ConceptID") == "concept_id"

    def test_to_pascal_case(self):
        """Test converting snake_case to PascalCase."""
        assert to_pascal_case("primary_criteria") == "PrimaryCriteria"
        assert to_pascal_case("concept_sets") == "ConceptSets"
        assert to_pascal_case("codeset_id") == "CodesetId"

    def test_dict_to_snake_case_simple(self):
        """Test converting dict keys to snake_case."""
        data = {"PrimaryCriteria": "value", "ConceptSets": []}
        result = dict_to_snake_case(data)
        assert "primary_criteria" in result
        assert "concept_sets" in result
        assert result["primary_criteria"] == "value"

    def test_dict_to_snake_case_nested(self):
        """Test converting nested dict keys to snake_case."""
        data = {"PrimaryCriteria": {"CriteriaList": [{"ConditionOccurrence": {"CodesetId": 1}}]}}
        result = dict_to_snake_case(data)
        assert "primary_criteria" in result
        assert "criteria_list" in result["primary_criteria"]
        assert isinstance(result["primary_criteria"]["criteria_list"], list)
        assert "condition_occurrence" in result["primary_criteria"]["criteria_list"][0]

    def test_dict_to_pascal_case_simple(self):
        """Test converting dict keys back to PascalCase."""
        data = {"primary_criteria": "value", "concept_sets": []}
        result = dict_to_pascal_case(data)
        assert "PrimaryCriteria" in result
        assert "ConceptSets" in result

    def test_dict_to_pascal_case_nested(self):
        """Test converting nested dict keys back to PascalCase."""
        data = {"primary_criteria": {"criteria_list": [{"condition_occurrence": {"codeset_id": 1}}]}}
        result = dict_to_pascal_case(data)
        assert "PrimaryCriteria" in result
        assert "CriteriaList" in result["PrimaryCriteria"]


class TestYAMLParsing:
    """Test YAML parsing and conversion."""

    @pytest.fixture
    def example_json_cohort(self):
        """Load the example JSON cohort from tests."""
        cohorts_dir = Path(__file__).parent / "cohorts"
        json_file = cohorts_dir / "isolated_immune_thrombocytopenia.json"
        if json_file.exists():
            return json.loads(json_file.read_text())
        # Return minimal valid cohort if file doesn't exist
        return {"concept_sets": [], "primary_criteria": None}

    def test_cohort_expression_from_yaml_simple(self):
        """Test parsing simple YAML cohort."""
        yaml_str = """
title: "Test Cohort"
concept_sets: []
primary_criteria: null
"""
        expr = cohort_expression_from_yaml(yaml_str)
        assert expr.title == "Test Cohort"
        assert expr.concept_sets == []

    def test_cohort_expression_from_yaml_with_criteria(self):
        """Test parsing YAML with more complex structure."""
        yaml_str = """
title: "Test Cohort"
concept_sets:
  - id: 1
    name: "Test Concept Set"
    expression:
      items: []
      is_excluded: false
      include_descendants: false
      include_mapped: false
primary_criteria: null
"""
        expr = cohort_expression_from_yaml(yaml_str)
        assert expr.title == "Test Cohort"
        assert len(expr.concept_sets) == 1
        assert expr.concept_sets[0].id == 1
        assert expr.concept_sets[0].name == "Test Concept Set"

    def test_cohort_expression_to_snake_case(self, example_json_cohort):
        """Test converting CohortExpression to snake_case dict."""
        import json

        from circe.api import cohort_expression_from_json

        json_str = json.dumps(example_json_cohort)
        expr = cohort_expression_from_json(json_str)
        result = cohort_expression_to_snake_case(expr)

        # Check that keys are in snake_case
        assert isinstance(result, dict)
        # Should not have PascalCase keys at top level
        assert "PrimaryCriteria" not in result
        assert "primary_criteria" in result or result == {}

    def test_snake_case_dict_to_cohort_expression(self):
        """Test converting snake_case dict to CohortExpression."""
        data = {
            "title": "Test Cohort",
            "concept_sets": [
                {
                    "id": 1,
                    "name": "Test",
                    "expression": {
                        "items": [],
                        "is_excluded": False,
                        "include_descendants": False,
                        "include_mapped": False,
                    },
                }
            ],
        }
        expr = snake_case_dict_to_cohort_expression(data)
        assert expr.title == "Test Cohort"
        assert len(expr.concept_sets) == 1


class TestYAMLIO:
    """Test YAML file I/O operations."""

    def test_save_expression_as_yaml(self):
        """Test saving CohortExpression to YAML file."""

        yaml_str = """
title: "Test Cohort"
concept_sets: []
"""
        expr = cohort_expression_from_yaml(yaml_str)

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_cohort.yaml"
            save_expression_as_yaml(expr, output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "test_cohort" in content.lower() or "Test Cohort" in content

    def test_load_expression_yaml_file(self):
        """Test loading YAML file via load_expression."""
        yaml_content = """
title: "Test Cohort"
concept_sets: []
"""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yaml"
            yaml_path.write_text(yaml_content)

            expr = load_expression(yaml_path)
            assert expr.title == "Test Cohort"

    def test_load_expression_yml_file(self):
        """Test loading .yml file extension."""
        yaml_content = """
title: "Test Cohort"
concept_sets: []
"""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yml"
            yaml_path.write_text(yaml_content)

            expr = load_expression(yaml_path)
            assert expr.title == "Test Cohort"

    def test_load_expression_json_still_works(self):
        """Test that JSON files still work via load_expression."""
        json_content = '{"title": "JSON Cohort", "conceptSets": []}'

        with TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test.json"
            json_path.write_text(json_content)

            expr = load_expression(json_path)
            assert expr.title == "JSON Cohort"


class TestRoundTrip:
    """Test round-trip conversions."""

    def test_yaml_to_json_roundtrip(self):
        """Test converting YAML -> JSON and back."""
        yaml_str = """
title: "Round Trip Test"
concept_sets: []
primary_criteria: null
"""
        # Load from YAML
        expr1 = cohort_expression_from_yaml(yaml_str)

        # Convert to dict and back
        snake_dict = cohort_expression_to_snake_case(expr1)
        expr2 = snake_case_dict_to_cohort_expression(snake_dict)

        assert expr1.title == expr2.title
        assert expr1.concept_sets == expr2.concept_sets

    def test_json_to_yaml_to_json(self):
        """Test converting JSON -> YAML -> JSON preserves equivalence."""
        # Create a minimal but valid cohort with primary_criteria
        example_json_cohort = {
            "title": "Round Trip Test",
            "concept_sets": [],
            "primary_criteria": {
                "criteria_list": [],
                "observation_window": {"prior_days": 0, "post_days": 0},
                "primary_criteria_limit": {"type": "All"},
            },
        }

        import json

        # Load from JSON
        json_str = json.dumps(example_json_cohort)
        expr1 = cohort_expression_from_json(json_str)

        # Save to YAML and reload
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "temp.yaml"
            save_expression_as_yaml(expr1, yaml_path)
            expr2 = load_expression(yaml_path)

            # Both should have same title
            assert expr1.title == expr2.title

            # Both should be able to generate SQL with same options
            options = BuildExpressionQueryOptions()
            sql1 = build_cohort_query(expr1, options)
            sql2 = build_cohort_query(expr2, options)
            # SQL should be identical for same input
            assert sql1 == sql2

    def test_yaml_preserves_snake_case_on_roundtrip(self):
        """Test that YAML round-trip preserves snake_case formatting."""
        yaml_str = """
title: "Snake Case Test"
concept_sets: []
inclusion_rules: []
"""
        expr = cohort_expression_from_yaml(yaml_str)

        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "temp.yaml"
            save_expression_as_yaml(expr, yaml_path)
            content = yaml_path.read_text()

            # Should have snake_case keys
            data = yaml.safe_load(content)
            # Find a key that should be in snake_case
            assert any(key for key in data if "_" in key or key in ["title"])


class TestCLIIntegration:
    """Test CLI commands with YAML files."""

    def test_yaml_file_with_validate_command(self):
        """Test validate command with YAML input."""
        yaml_content = """
title: "CLI Test Cohort"
concept_sets: []
"""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yaml"
            yaml_path.write_text(yaml_content)

            # load_expression should handle it
            expr = load_expression(yaml_path)
            assert expr.title == "CLI Test Cohort"

    def test_yaml_file_with_sql_generation(self):
        """Test SQL generation from YAML input."""
        yaml_content = """
title: "SQL Generation Test"
concept_sets: []
primary_criteria:
  criteria_list: []
  observation_window:
    prior_days: 0
    post_days: 0
  primary_criteria_limit:
    type: "All"
"""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "test.yaml"
            yaml_path.write_text(yaml_content)

            expr = load_expression(yaml_path)
            options = BuildExpressionQueryOptions()
            sql = build_cohort_query(expr, options)

            assert isinstance(sql, str)
            # Should contain some SQL
            assert len(sql) > 0


@pytest.fixture
def example_json_cohort():
    """Load the example JSON cohort from tests."""
    cohorts_dir = Path(__file__).parent / "cohorts"
    json_file = cohorts_dir / "isolated_immune_thrombocytopenia.json"
    if json_file.exists():
        return json.loads(json_file.read_text())
    # Return minimal valid cohort if file doesn't exist
    return {"concept_sets": [], "primary_criteria": None}
