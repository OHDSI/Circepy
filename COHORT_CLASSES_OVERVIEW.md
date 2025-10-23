"""
CIRCE Python Implementation - Cohort Expression Classes

This document provides an overview of the Python class representations created from the JSON schema
for the CIRCE-BE cohort expression system.

## Overview

The implementation provides Pydantic-based Python classes that mirror the Java CIRCE-BE structure,
enabling the creation and manipulation of cohort expressions in Python.

## Package Structure

```
circe/
├── __init__.py                 # Main package exports
├── cohortdefinition/          # Cohort definition classes
│   ├── __init__.py            # Cohort definition exports
│   ├── core.py                # Core classes and enums
│   ├── criteria.py             # Criteria-related classes
│   ├── cohort.py               # Main CohortExpression class
│   └── interfaces.py           # Base interfaces
└── vocabulary/                 # Vocabulary classes
    ├── __init__.py            # Vocabulary exports
    └── concept.py              # Concept and concept set classes
```

## Main Classes

### Core Classes (core.py)

- **CollapseType**: Enum for collapse types (COLLAPSE, NO_COLLAPSE)
- **DateType**: Enum for date types (START_DATE, END_DATE)
- **ResultLimit**: Result limit configuration
- **Period**: Time period with start/end dates
- **DateRange**: Date range with operation, extent, and value
- **NumericRange**: Numeric range with operation, value, and extent
- **DateAdjustment**: Date adjustment settings
- **ObservationFilter**: Observation window filter settings
- **CollapseSettings**: Collapse settings for cohort expressions
- **EndStrategy**: End strategy configuration
- **PrimaryCriteria**: Primary criteria for cohort definition
- **CriteriaGroup**: Group of criteria with logical operators
- **ConceptSetSelection**: Concept set selection configuration

### Criteria Classes (criteria.py)

- **CriteriaColumn**: Represents a criteria column
- **Occurrence**: Occurrence settings for criteria
- **CorelatedCriteria**: Correlated criteria
- **DemographicCriteria**: Demographic criteria for cohort definition
- **Criteria**: Criteria with date adjustment and correlated criteria
- **InclusionRule**: Inclusion rule for cohort definition

### Vocabulary Classes (concept.py)

- **Concept**: Represents a concept in the OMOP vocabulary
- **ConceptSetItem**: Item in a concept set
- **ConceptSetExpression**: Concept set expression
- **ConceptSet**: Concept set container

### Main Cohort Class (cohort.py)

- **CohortExpression**: Main cohort expression class containing all components

### Interface Classes (interfaces.py)

*Note: Interface classes have been removed as they were not being used by any concrete classes.*

## Key Features

### Field Aliases
All classes support both camelCase (JSON) and snake_case (Python) field names through Pydantic aliases.

### Validation
Classes include basic validation methods and Pydantic's built-in validation.

### Type Safety
Full type hints are provided for all fields and methods.

## Usage Example

```python
from circe import CohortExpression, Concept, ConceptSet

# Create a concept
concept = Concept(concept_id=12345, concept_name="Diabetes")

# Create a concept set
concept_set = ConceptSet(id=1, name="Diabetes Concepts")

# Create a cohort expression
cohort_expr = CohortExpression(
    title="Diabetes Cohort",
    concept_sets=[concept_set],
    primary_criteria=PrimaryCriteria()
)

# Validate the expression
is_valid = cohort_expr.validate_expression()
```

## JSON Schema Mapping

The classes are designed to match the JSON schema structure from `java_cohort_expression_schema.json`:

- All field names support both camelCase (from JSON) and snake_case (Python convention)
- Required fields are enforced through Pydantic validation
- Optional fields are properly typed as Optional[T]
- Complex nested structures are supported through proper class composition

## Dependencies

- **pydantic**: For data validation and serialization
- **typing**: For type hints and annotations
- **enum**: For enumeration types

## Future Enhancements

The current implementation provides the core data structures. Future enhancements could include:

1. **Builders**: Fluent API builders for easier cohort construction
2. **Print-friendly**: Human-readable output generation
3. **SQL Generation**: Conversion to SQL queries
4. **Validation**: Enhanced validation rules
5. **Serialization**: JSON/XML import/export utilities

## Testing

The implementation has been tested for:
- Successful imports of all classes
- Basic instantiation of core classes
- Field alias functionality (camelCase ↔ snake_case)
- Pydantic validation and serialization

All tests pass successfully, confirming the implementation is working correctly.
"""
