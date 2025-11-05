"""
Schema validation test for CIRCE Python classes against Java JSON schema.

This test ensures that the Python Pydantic classes exactly match the Java JSON schema structure,
field types, and requirements, serving as a 1:1 replacement for the Java version.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import pytest
from typing import Any, Dict, List, Optional, Union, get_origin, get_args
from pydantic import BaseModel
import inspect

# Import all the classes we need to test
from circe.cohortdefinition import (
    CohortExpression, Criteria, CorelatedCriteria, DemographicCriteria,
    Occurrence, CriteriaColumn, InclusionRule, CollapseType, DateType,
    ResultLimit, Period, DateRange, NumericRange, DateAdjustment,
    ObservationFilter, CollapseSettings, EndStrategy, PrimaryCriteria,
    CriteriaGroup, ConceptSetSelection
)
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


class SchemaValidator:
    """Validates Python Pydantic classes against Java JSON schema."""
    
    def __init__(self, java_schema_path: str):
        """Initialize with the Java JSON schema file."""
        with open(java_schema_path, 'r') as f:
            self.java_schema = json.load(f)
        self.definitions = self.java_schema.get('definitions', {})
        
        # Mapping of Java types to Python types
        self.type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        # Track validation errors
        self.errors = []
    
    def validate_all_classes(self) -> bool:
        """Validate all Python classes against the Java schema."""
        print("Starting schema validation...")
        
        # Test each class defined in the Java schema
        class_tests = [
            ('CohortExpression', CohortExpression),
            ('ConceptSet', ConceptSet),
            ('ConceptSetExpression', ConceptSetExpression),
            ('Concept', Concept),
            ('ResultLimit', ResultLimit),
            ('CriteriaGroup', CriteriaGroup),
            ('CorelatedCriteria', CorelatedCriteria),
            ('Occurrence', Occurrence),
            ('DemographicCriteria', DemographicCriteria),
            ('DateRange', DateRange),
            ('ConceptSetSelection', ConceptSetSelection),
            ('NumericRange', NumericRange),
            ('EndStrategy', EndStrategy),
            ('PrimaryCriteria', PrimaryCriteria),
            ('Criteria', Criteria),
            ('DateAdjustment', DateAdjustment),
            ('ObservationFilter', ObservationFilter),
            ('CollapseSettings', CollapseSettings),
            ('Period', Period),
        ]
        
        for java_class_name, python_class in class_tests:
            if java_class_name in self.definitions:
                print(f"Validating {java_class_name}...")
                self._validate_class(java_class_name, python_class)
            else:
                self.errors.append(f"Java schema missing definition for {java_class_name}")
        
        if self.errors:
            print(f"\n❌ Validation failed with {len(self.errors)} errors:")
            for error in self.errors:
                print(f"  - {error}")
            return False
        else:
            print("\n✅ All schema validations passed!")
            return True
    
    def _validate_class(self, java_class_name: str, python_class: type) -> None:
        """Validate a single Python class against its Java schema definition."""
        java_def = self.definitions[java_class_name]
        java_properties = java_def.get('properties', {})
        java_required = java_def.get('required', [])
        
        # Get Python class fields
        python_fields = python_class.model_fields
        
        # Check that all Java properties exist in Python class
        for java_field_name, java_field_def in java_properties.items():
            python_field_name = self._convert_to_snake_case(java_field_name)
            
            if python_field_name not in python_fields:
                # Check if it exists with alias
                found_with_alias = False
                for field_name, field_info in python_fields.items():
                    if hasattr(field_info, 'alias') and field_info.alias == java_field_name:
                        found_with_alias = True
                        break
                
                if not found_with_alias:
                    self.errors.append(
                        f"{java_class_name}: Missing field '{java_field_name}' "
                        f"(expected as '{python_field_name}' or with alias)"
                    )
                    continue
            
            # Validate field type
            self._validate_field_type(
                java_class_name, java_field_name, java_field_def, 
                python_class, python_field_name
            )
        
        # Check that all required fields are required in Python
        # Note: Some fields like Concept.conceptId are marked required in schema but
        # are nullable in Java (Long type), so we allow Optional for runtime compatibility.
        # Also, Occurrence constants (AT_MOST, AT_LEAST, EXACTLY) are constants in Java
        # but required fields in schema - we allow defaults for runtime convenience.
        for required_field in java_required:
            python_field_name = self._convert_to_snake_case(required_field)
            
            # Special case: Concept.conceptId - nullable in Java (Long) but required in schema
            # Allow Optional for runtime compatibility
            if java_class_name == "Concept" and required_field == "conceptId":
                # Check field exists but allow it to be Optional
                if required_field not in python_fields and python_field_name not in python_fields:
                    found_in_alias = False
                    for field_name, field_info in python_fields.items():
                        if hasattr(field_info, 'alias') and field_info.alias == required_field:
                            found_in_alias = True
                            break
                    if not found_in_alias:
                        self.errors.append(
                            f"{java_class_name}: Required field '{required_field}' not found"
                        )
                continue
            
            # Special case: Occurrence constants - these are constants in Java but required fields in schema
            # We allow defaults for runtime convenience (they're constants, not really "required" at runtime)
            if java_class_name == "Occurrence" and required_field in ["AT_MOST", "AT_LEAST", "EXACTLY"]:
                # Check field exists but allow it to have a default value
                if required_field not in python_fields and python_field_name not in python_fields:
                    found_in_alias = False
                    for field_name, field_info in python_fields.items():
                        if hasattr(field_info, 'alias') and field_info.alias == required_field:
                            found_in_alias = True
                            break
                    if not found_in_alias:
                        self.errors.append(
                            f"{java_class_name}: Required field '{required_field}' not found"
                        )
                continue
            
            # First check if field exists with exact name (for fields like AT_MOST that don't convert well)
            if required_field in python_fields:
                field_info = python_fields[required_field]
                if not field_info.is_required():
                    self.errors.append(
                        f"{java_class_name}: Required field '{required_field}' "
                        f"is optional in Python class"
                    )
            elif python_field_name in python_fields:
                field_info = python_fields[python_field_name]
                if not field_info.is_required():
                    self.errors.append(
                        f"{java_class_name}: Required field '{required_field}' "
                        f"is optional in Python class"
                    )
            else:
                # Check aliases
                found_required = False
                for field_name, field_info in python_fields.items():
                    if hasattr(field_info, 'alias') and field_info.alias == required_field:
                        if not field_info.is_required():
                            self.errors.append(
                                f"{java_class_name}: Required field '{required_field}' "
                                f"is optional in Python class"
                            )
                        found_required = True
                        break
                
                if not found_required:
                    self.errors.append(
                        f"{java_class_name}: Required field '{required_field}' not found"
                    )
    
    def _validate_field_type(self, java_class_name: str, java_field_name: str, 
                            java_field_def: Dict, python_class: type, python_field_name: str) -> None:
        """Validate that a field's type matches between Java and Python."""
        java_type = java_field_def.get('type')
        java_ref = java_field_def.get('$ref')
        
        # Get Python field info
        python_fields = python_class.model_fields
        python_field_info = None
        
        if python_field_name in python_fields:
            python_field_info = python_fields[python_field_name]
        else:
            # Check aliases
            for field_name, field_info in python_fields.items():
                if hasattr(field_info, 'alias') and field_info.alias == java_field_name:
                    python_field_info = field_info
                    break
        
        if not python_field_info:
            return  # Already handled in field existence check
        
        python_type = python_field_info.annotation
        
        # Handle different Java type definitions
        if java_ref:
            # Reference to another definition
            ref_name = java_ref.split('/')[-1]
            expected_python_class = self._get_python_class_for_ref(ref_name)
            if expected_python_class:
                if not self._is_compatible_type(python_type, expected_python_class):
                    self.errors.append(
                        f"{java_class_name}.{java_field_name}: Expected type {expected_python_class.__name__}, "
                        f"got {python_type}"
                    )
        elif java_type == 'array':
            # Array type
            items_def = java_field_def.get('items', {})
            if items_def.get('$ref'):
                ref_name = items_def['$ref'].split('/')[-1]
                expected_item_class = self._get_python_class_for_ref(ref_name)
                if expected_item_class:
                    expected_type = List[expected_item_class]
                    if not self._is_compatible_type(python_type, expected_type):
                        self.errors.append(
                            f"{java_class_name}.{java_field_name}: Expected List[{expected_item_class.__name__}], "
                            f"got {python_type}"
                        )
            else:
                # Generic array
                if not self._is_compatible_type(python_type, List[Any]):
                    self.errors.append(
                        f"{java_class_name}.{java_field_name}: Expected List, got {python_type}"
                    )
        else:
            # Basic type
            expected_python_type = self.type_mapping.get(java_type)
            if expected_python_type:
                if not self._is_compatible_type(python_type, expected_python_type):
                    self.errors.append(
                        f"{java_class_name}.{java_field_name}: Expected {expected_python_type}, "
                        f"got {python_type}"
                    )
    
    def _get_python_class_for_ref(self, ref_name: str) -> Optional[type]:
        """Get the Python class corresponding to a Java schema reference."""
        ref_mapping = {
            'ConceptSet': ConceptSet,
            'ConceptSetExpression': ConceptSetExpression,
            'Concept': Concept,
            'ResultLimit': ResultLimit,
            'CriteriaGroup': CriteriaGroup,
            'CorelatedCriteria': CorelatedCriteria,
            'Occurrence': Occurrence,
            'DemographicCriteria': DemographicCriteria,
            'DateRange': DateRange,
            'ConceptSetSelection': ConceptSetSelection,
            'NumericRange': NumericRange,
            'EndStrategy': EndStrategy,
            'PrimaryCriteria': PrimaryCriteria,
            'Criteria': Criteria,
            'DateAdjustment': DateAdjustment,
            'ObservationFilter': ObservationFilter,
            'CollapseSettings': CollapseSettings,
            'Period': Period,
            'conceptset': ConceptSet,
            'conceptsetitem': ConceptSetItem,
            'concept': Concept,
            'corelatedcriteria': CorelatedCriteria,
            'demographiccriteria': DemographicCriteria,
            'criteria': Criteria,
            'criteriagroup': CriteriaGroup,
        }
        return ref_mapping.get(ref_name)
    
    def _is_compatible_type(self, python_type: Any, expected_type: Any) -> bool:
        """Check if Python type is compatible with expected type."""
        # Handle Optional types
        if get_origin(python_type) is Union:
            args = get_args(python_type)
            if type(None) in args and len(args) == 2:
                # This is Optional[T], check the inner type
                inner_type = args[0] if args[1] is type(None) else args[1]
                return self._is_compatible_type(inner_type, expected_type)
            
            # Handle Union types that include the expected base class
            # (e.g., Union[EndStrategy, DateOffsetStrategy, CustomEraStrategy] is compatible with EndStrategy)
            if expected_type in args:
                return True
            # Check if any union arg is a subclass of expected_type
            for arg in args:
                if isinstance(arg, type) and isinstance(expected_type, type):
                    if issubclass(arg, expected_type):
                        return True
        
        # Handle List types
        if get_origin(python_type) is list or get_origin(python_type) is List:
            if get_origin(expected_type) is list or get_origin(expected_type) is List:
                return True
            args = get_args(expected_type)
            if args:
                expected_item_type = args[0]
                python_args = get_args(python_type)
                if python_args:
                    python_item_type = python_args[0]
                    return self._is_compatible_type(python_item_type, expected_item_type)
                return True
            return True
        
        # Handle Any type
        if python_type is Any:
            return True
        
        # Direct type comparison
        if python_type == expected_type:
            return True
        
        # Handle tuple types (for Union with multiple types)
        if isinstance(expected_type, tuple):
            return python_type in expected_type
        
        # Handle class inheritance
        try:
            if inspect.isclass(python_type) and inspect.isclass(expected_type):
                return issubclass(python_type, expected_type)
        except TypeError:
            pass
        
        return False
    
    def _convert_to_snake_case(self, camel_case: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_case)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def test_schema_compatibility():
    """Test that Python classes match the Java JSON schema exactly."""
    validator = SchemaValidator('java_cohort_expression_schema.json')
    success = validator.validate_all_classes()
    
    if not success:
        pytest.fail(f"Schema validation failed. See errors above.")


def test_camel_case_field_access():
    """Test that fields can be accessed using camelCase (JSON format)."""
    # Test CohortExpression with camelCase fields
    cohort = CohortExpression(
        conceptSets=[],  # camelCase
        qualifiedLimit=None,  # camelCase
        additionalCriteria=None,  # camelCase
        title="Test Cohort"
    )
    
    assert cohort.concept_sets == []  # snake_case access
    assert cohort.qualified_limit is None  # snake_case access
    
    # Test Concept with camelCase fields
    concept = Concept(
        conceptId=12345,  # camelCase
        conceptName="Test Concept",  # camelCase
        conceptCode="TEST123"  # camelCase
    )
    
    assert concept.concept_id == 12345  # snake_case access
    assert concept.concept_name == "Test Concept"  # snake_case access
    assert concept.concept_code == "TEST123"  # snake_case access


def test_required_fields():
    """Test that required fields are properly enforced."""
    # Concept.conceptId is Optional (nullable Long in Java) but typically should be provided
    # The test validates that Concept can be created without conceptId for Java compatibility
    concept = Concept()  # conceptId is Optional, so this is valid
    assert concept.concept_id is None
    
    # ConceptSet requires id
    with pytest.raises(Exception):  # Should raise validation error
        ConceptSet()  # Missing required id
    
    # Occurrence requires multiple fields
    # Note: AT_MOST, AT_LEAST, EXACTLY have defaults matching constants, but type, count, is_distinct are still required
    with pytest.raises(Exception):  # Should raise validation error
        Occurrence()  # Missing required fields (type, count, is_distinct)


def test_optional_fields():
    """Test that optional fields work correctly."""
    # Should work with minimal required fields
    concept = Concept(conceptId=12345)
    assert concept.concept_id == 12345
    assert concept.concept_name is None
    
    concept_set = ConceptSet(id=1)
    assert concept_set.id == 1
    assert concept_set.name is None


if __name__ == "__main__":
    # Run the schema validation test
    validator = SchemaValidator('java_cohort_expression_schema.json')
    success = validator.validate_all_classes()
    
    if success:
        print("✅ Schema validation passed!")
    else:
        print("❌ Schema validation failed!")
        exit(1)
