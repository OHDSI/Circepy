"""
Basic tests for CIRCE Python package structure.

These tests verify that the package can be imported and basic structure is in place.
"""

import pytest

import circe


class TestPackageStructure:
    """Test basic package structure and imports."""

    def test_package_import(self):
        """Test that the main package can be imported."""
        assert hasattr(circe, "__version__")

    def test_package_metadata(self):
        """Test package metadata."""
        assert hasattr(circe, "__author__")
        assert hasattr(circe, "__email__")
        assert hasattr(circe, "__license__")
        assert circe.__author__ == "CIRCE Python Implementation Team"
        assert circe.__email__ == "circe-python@ohdsi.org"
        assert circe.__license__ == "Apache License 2.0"

    def test_subpackage_imports(self):
        """Test that subpackages can be imported."""
        import circe.check
        import circe.check.checkers
        import circe.check.operations
        import circe.check.utils
        import circe.check.warnings
        import circe.cohortdefinition

        # Test sub-subpackages
        import circe.cohortdefinition.builders
        import circe.cohortdefinition.printfriendly
        import circe.execution
        import circe.helper
        import circe.vocabulary

    def test_package_structure(self):
        """Test that package structure matches expected layout."""
        import circe

        # Check that main package has expected attributes
        expected_attrs = ["__version__", "__author__", "__email__", "__license__"]
        for attr in expected_attrs:
            assert hasattr(circe, attr), f"Missing attribute: {attr}"

    def test_main_exports(self):
        """Test that main classes are properly exported."""
        # These should be available at the package level
        assert hasattr(circe, "__all__")
        assert isinstance(circe.__all__, list)

        # Should include metadata and main classes
        expected_exports = [
            "__version__",
            "__author__",
            "__email__",
            "__license__",
            "CohortExpression",
            "Concept",
            "ConceptSet",
            "ConceptSetExpression",
            "ConceptSetItem",
        ]

        for export in expected_exports:
            assert export in circe.__all__, f"Missing export: {export}"

    def test_main_class_imports(self):
        """Test that main classes can be imported and instantiated."""
        # Test that classes are available at package level
        from circe import (
            CohortExpression,
            Concept,
            ConceptSet,
            ConceptSetExpression,
            ConceptSetItem,
        )

        # Test basic instantiation
        concept = Concept(conceptId=12345)
        assert concept.concept_id == 12345

        concept_set = ConceptSet(id=1)
        assert concept_set.id == 1

        cohort_expr = CohortExpression(title="Test")
        assert cohort_expr.title == "Test"


class TestModuleStructure:
    """Test individual module structure."""

    def test_cohortdefinition_module(self):
        """Test cohortdefinition module structure."""
        import circe.cohortdefinition

        assert hasattr(circe.cohortdefinition, "__all__")

    def test_vocabulary_module(self):
        """Test vocabulary module structure."""
        import circe.vocabulary

        assert hasattr(circe.vocabulary, "__all__")

    def test_check_module(self):
        """Test check module structure."""
        import circe.check

        assert hasattr(circe.check, "__all__")

    def test_helper_module(self):
        """Test helper module structure."""
        import circe.helper

        assert hasattr(circe.helper, "__all__")


if __name__ == "__main__":
    pytest.main([__file__])
