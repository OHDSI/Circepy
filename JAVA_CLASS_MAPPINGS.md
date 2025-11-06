"""
Java Class Mappings for CIRCE Python Implementation

This document provides a comprehensive mapping of Python classes to their equivalent
Java CIRCE-BE classes, showing the 1:1 correspondence between implementations.

## Cohort Definition Classes

### Core Classes (`circe.cohortdefinition.core`)

| Python Class | Java Equivalent | Description |
|--------------|-----------------|-------------|
| `CollapseType` | `org.ohdsi.circe.cohortdefinition.CollapseType` | Enumeration for collapse types |
| `DateType` | `org.ohdsi.circe.cohortdefinition.DateType` | Enumeration for date types |
| `ResultLimit` | `org.ohdsi.circe.cohortdefinition.ResultLimit` | Result limit configuration |
| `Period` | `org.ohdsi.circe.cohortdefinition.Period` | Time period with start/end dates |
| `DateRange` | `org.ohdsi.circe.cohortdefinition.DateRange` | Date range with operation, extent, value |
| `NumericRange` | `org.ohdsi.circe.cohortdefinition.NumericRange` | Numeric range with operation, value, extent |
| `DateAdjustment` | `org.ohdsi.circe.cohortdefinition.DateAdjustment` | Date adjustment settings |
| `ObservationFilter` | `org.ohdsi.circe.cohortdefinition.ObservationFilter` | Observation window filter settings |
| `CollapseSettings` | `org.ohdsi.circe.cohortdefinition.CollapseSettings` | Collapse settings for cohort expressions |
| `EndStrategy` | `org.ohdsi.circe.cohortdefinition.EndStrategy` | End strategy configuration |
| `PrimaryCriteria` | `org.ohdsi.circe.cohortdefinition.PrimaryCriteria` | Primary criteria for cohort definition |
| `CriteriaGroup` | `org.ohdsi.circe.cohortdefinition.CriteriaGroup` | Group of criteria with logical operators |
| `ConceptSetSelection` | `org.ohdsi.circe.cohortdefinition.ConceptSetSelection` | Concept set selection configuration |

### Criteria Classes (`circe.cohortdefinition.criteria`)

| Python Class | Java Equivalent | Description |
|--------------|-----------------|-------------|
| `CriteriaColumn` | `org.ohdsi.circe.cohortdefinition.CriteriaColumn` | Represents a criteria column |
| `Occurrence` | `org.ohdsi.circe.cohortdefinition.Occurrence` | Occurrence settings for criteria |
| `CorelatedCriteria` | `org.ohdsi.circe.cohortdefinition.CorelatedCriteria` | Correlated criteria |
| `DemographicCriteria` | `org.ohdsi.circe.cohortdefinition.DemographicCriteria` | Demographic criteria for cohort definition |
| `Criteria` | `org.ohdsi.circe.cohortdefinition.Criteria` | Criteria with date adjustment and correlated criteria |
| `InclusionRule` | `org.ohdsi.circe.cohortdefinition.InclusionRule` | Inclusion rule for cohort definition with expression, description, and name |

### Main Cohort Class (`circe.cohortdefinition.cohort`)

| Python Class | Java Equivalent | Description |
|--------------|-----------------|-------------|
| `CohortExpression` | `org.ohdsi.circe.cohortdefinition.CohortExpression` | Main cohort expression class containing all components |

## Vocabulary Classes

### Concept Classes (`circe.vocabulary.concept`)

| Python Class | Java Equivalent | Description |
|--------------|-----------------|-------------|
| `Concept` | `org.ohdsi.circe.vocabulary.Concept` | Represents a concept in the OMOP vocabulary |
| `ConceptSetItem` | `org.ohdsi.circe.vocabulary.ConceptSetItem` | Item in a concept set |
| `ConceptSetExpression` | `org.ohdsi.circe.vocabulary.ConceptSetExpression` | Concept set expression |
| `ConceptSet` | `org.ohdsi.circe.cohortdefinition.ConceptSet` | Concept set container |

## Interface Classes

*Note: The interface classes have been removed as they were not being used by any concrete classes.*

## Package Structure Mapping

### Java Package Structure
```
org.ohdsi.circe.cohortdefinition.*
org.ohdsi.circe.vocabulary.*
```

### Python Package Structure
```
circe.cohortdefinition.*
circe.vocabulary.*
```

## Field Name Mapping

### Java to Python Field Names
- **Java**: camelCase (e.g., `conceptId`, `conceptName`)
- **Python**: snake_case (e.g., `concept_id`, `concept_name`)
- **Aliases**: Python classes support both formats through Pydantic aliases

### Example Field Mappings

**Note**: Java JSON uses different casing conventions for different field types:
- **Criteria fields**: PascalCase (e.g., `CodesetId`, `ConditionTypeExclude`)
- **ConceptSet simple fields**: lowercase (e.g., `id`, `name`, `expression`, `items`)
- **Boolean/option fields**: camelCase (e.g., `isExcluded`, `includeMapped`, `includeDescendants`)
- **Concept fields**: ALL_CAPS (e.g., `CONCEPT_ID`, `CONCEPT_NAME`)

| Java Field | Python Field | Python Alias | Notes |
|------------|--------------|--------------|-------|
| `CodesetId` | `codeset_id` | `CodesetId` | Criteria field - PascalCase |
| `ConditionTypeExclude` | `condition_type_exclude` | `ConditionTypeExclude` | Criteria field - PascalCase |
| `ConceptSets` | `concept_sets` | `ConceptSets` | Top-level field - PascalCase |
| `PrimaryCriteria` | `primary_criteria` | `PrimaryCriteria` | Top-level field - PascalCase |
| `id` | `id` | (no alias) | ConceptSet field - lowercase |
| `name` | `name` | (no alias) | ConceptSet field - lowercase |
| `expression` | `expression` | (no alias) | ConceptSet field - lowercase |
| `isExcluded` | `is_excluded` | `isExcluded` | Boolean field - camelCase |
| `includeMapped` | `include_mapped` | `includeMapped` | Boolean field - camelCase |
| `includeDescendants` | `include_descendants` | `includeDescendants` | Boolean field - camelCase |
| `CONCEPT_ID` | `concept_id` | `CONCEPT_ID` | Concept field - ALL_CAPS |
| `CONCEPT_NAME` | `concept_name` | `CONCEPT_NAME` | Concept field - ALL_CAPS |

## Usage Examples

### Creating Objects with Java Field Names
```python
# Using Java-style field names (camelCase)
concept = Concept(conceptId=12345, conceptName="Diabetes")
cohort = CohortExpression(title="Test Cohort", conceptSets=[])
```

### Creating Objects with Python Field Names
```python
# Using Python-style field names (snake_case)
concept = Concept(concept_id=12345, concept_name="Diabetes")
cohort = CohortExpression(title="Test Cohort", concept_sets=[])
```

### Accessing Fields
```python
# Both access patterns work
assert concept.concept_id == concept.conceptId
assert cohort.concept_sets == cohort.conceptSets
```

## JSON Export Format

When exporting Python cohort definitions to JSON for use with Java tools, use:

```python
# Export with Java-compatible field names
json_str = cohort.model_dump_json(by_alias=True, exclude_none=True)

# Or as a dictionary
json_dict = cohort.model_dump(by_alias=True, exclude_none=True)
```

### Polymorphic Criteria Wrapping

Criteria objects are automatically wrapped in their type names for Java compatibility:

```python
# Python object
condition = ConditionOccurrence(codeset_id=6, condition_type_exclude=False)

# Exported JSON (automatically wrapped)
{
  "ConditionOccurrence": {
    "CodesetId": 6,
    "ConditionTypeExclude": false
  }
}
```

### Field Name Casing

The export uses Java's mixed casing convention:
- **Top-level fields**: PascalCase (`ConceptSets`, `PrimaryCriteria`)
- **Criteria fields**: PascalCase (`CodesetId`, `ConditionTypeExclude`)
- **ConceptSet simple fields**: lowercase (`id`, `name`, `expression`, `items`)
- **Boolean fields**: camelCase (`isExcluded`, `includeMapped`)
- **Concept fields**: ALL_CAPS (`CONCEPT_ID`, `CONCEPT_NAME`)

## Validation and Compatibility

All Python classes have been validated against the Java JSON schema to ensure:
- ✅ Exact field matching
- ✅ Type compatibility
- ✅ Required field enforcement
- ✅ Nested structure compatibility
- ✅ Java JSON export compatibility
- ✅ Polymorphic criteria serialization

The Python implementation serves as a true 1:1 replacement for the Java version with
guaranteed schema compatibility and comprehensive validation testing.
"""
