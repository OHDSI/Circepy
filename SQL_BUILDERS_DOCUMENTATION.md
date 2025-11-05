"""
SQL Query Builders Documentation

This document provides an overview of the SQL query builders implemented in the Python
CIRCE implementation, mirroring the Java CIRCE-BE builder classes.

## Overview

The SQL builders generate SQL queries from cohort definition criteria, providing a
programmatic way to create complex cohort queries. Each builder corresponds to a
specific OMOP CDM table and generates appropriate SQL for querying that table.

## Architecture

### Base Classes

#### BuilderUtils
**Java equivalent**: `org.ohdsi.circe.cohortdefinition.builders.BuilderUtils`

Utility class containing static methods for SQL query building:
- `get_date_adjustment_expression()` - Generate date adjustment SQL
- `get_codeset_join_expression()` - Generate codeset join SQL
- `get_codeset_in_expression()` - Generate codeset IN clause SQL
- `get_concept_ids_from_concepts()` - Extract concept IDs from concept lists
- `build_date_range_clause()` - Build date range WHERE clauses
- `build_numeric_range_clause()` - Build numeric range WHERE clauses
- `build_text_filter_clause()` - Build text filter WHERE clauses

#### BuilderOptions
**Java equivalent**: `org.ohdsi.circe.cohortdefinition.builders.BuilderOptions`

Configuration class for builder options:
- `additional_columns` - List of additional columns to include in queries

#### CriteriaColumn
**Java equivalent**: `org.ohdsi.circe.cohortdefinition.builders.CriteriaColumn`

Enumeration of available criteria columns:
- `START_DATE` - Start date column
- `END_DATE` - End date column
- `VISIT_ID` - Visit occurrence ID column
- `DOMAIN_CONCEPT` - Domain concept ID column
- `DURATION` - Duration calculation column
- `AGE` - Age column
- `GENDER` - Gender column
- `RACE` - Race column
- `ETHNICITY` - Ethnicity column

#### CriteriaSqlBuilder
**Java equivalent**: `org.ohdsi.circe.cohortdefinition.builders.CriteriaSqlBuilder`

Abstract base class for all SQL builders:
- `get_criteria_sql()` - Generate SQL for criteria
- `get_criteria_sql_with_options()` - Generate SQL with builder options
- `get_query_template()` - Get SQL template (abstract)
- `get_default_columns()` - Get default columns (abstract)
- `get_table_column_for_criteria_column()` - Map criteria columns to table columns (abstract)

### Specific Builders

#### ConditionOccurrenceSqlBuilder
**Java equivalent**: `org.ohdsi.circe.cohortdefinition.builders.ConditionOccurrenceSqlBuilder`

Generates SQL queries for condition occurrence criteria:
- **Table**: `CONDITION_OCCURRENCE`
- **Default columns**: `START_DATE`, `END_DATE`, `VISIT_ID`
- **Key mappings**:
  - `DOMAIN_CONCEPT` → `C.condition_concept_id`
  - `DURATION` → `(DATEDIFF(d,C.start_date, C.end_date))`
  - `START_DATE` → `C.start_date`
  - `END_DATE` → `C.end_date`

#### DrugExposureSqlBuilder
**Java equivalent**: `org.ohdsi.circe.cohortdefinition.builders.DrugExposureSqlBuilder`

Generates SQL queries for drug exposure criteria:
- **Table**: `DRUG_EXPOSURE`
- **Default columns**: `START_DATE`, `END_DATE`, `VISIT_ID`
- **Key mappings**:
  - `DOMAIN_CONCEPT` → `C.drug_concept_id`
  - `DURATION` → `(DATEDIFF(d,C.drug_exposure_start_date, C.drug_exposure_end_date))`
  - `START_DATE` → `C.drug_exposure_start_date`
  - `END_DATE` → `C.drug_exposure_end_date`

#### ProcedureOccurrenceSqlBuilder
**Java equivalent**: `org.ohdsi.circe.cohortdefinition.builders.ProcedureOccurrenceSqlBuilder`

Generates SQL queries for procedure occurrence criteria:
- **Table**: `PROCEDURE_OCCURRENCE`
- **Default columns**: `START_DATE`, `END_DATE`, `VISIT_ID`
- **Key mappings**:
  - `DOMAIN_CONCEPT` → `C.procedure_concept_id`
  - `DURATION` → `0` (procedures typically don't have duration)
  - `START_DATE` → `C.procedure_date`
  - `END_DATE` → `C.procedure_date`

## SQL Template Structure

Each builder uses SQL templates with placeholders that are replaced during query generation:

```sql
-- Begin [Domain] Criteria
SELECT C.person_id, C.[domain]_id as event_id, C.[start_date], C.[end_date],
  C.visit_occurrence_id, C.[start_date] as sort_date@additionalColumns
FROM 
(
  SELECT @selectClause @ordinalExpression
  FROM @cdm_database_schema.[TABLE_NAME] [alias]
  @codesetClause
) C
@joinClause
@whereClause
-- End [Domain] Criteria
```

### Template Placeholders

- `@additionalColumns` - Additional columns from BuilderOptions
- `@selectClause` - SELECT clause columns
- `@ordinalExpression` - Ordinal expression for ranking
- `@cdm_database_schema` - CDM database schema name
- `@codesetClause` - Codeset join clauses
- `@joinClause` - Additional JOIN clauses
- `@whereClause` - WHERE clause conditions

## Usage Examples

### Basic Usage

```python
from circe.cohortdefinition.builders import ConditionOccurrenceSqlBuilder
from circe.cohortdefinition import Criteria

# Create builder
builder = ConditionOccurrenceSqlBuilder()

# Create criteria
criteria = Criteria()

# Generate SQL
sql = builder.get_criteria_sql(criteria)
print(sql)
```

### With Builder Options

```python
from circe.cohortdefinition.builders import (
    ConditionOccurrenceSqlBuilder, 
    BuilderOptions, 
    CriteriaColumn
)

# Create builder with options
builder = ConditionOccurrenceSqlBuilder()
options = BuilderOptions()
options.additional_columns = [CriteriaColumn.DURATION, CriteriaColumn.AGE]

# Generate SQL with additional columns
sql = builder.get_criteria_sql_with_options(criteria, options)
print(sql)
```

### Multiple Builders

```python
from circe.cohortdefinition.builders import (
    ConditionOccurrenceSqlBuilder,
    DrugExposureSqlBuilder,
    ProcedureOccurrenceSqlBuilder
)

builders = [
    ConditionOccurrenceSqlBuilder(),
    DrugExposureSqlBuilder(),
    ProcedureOccurrenceSqlBuilder()
]

for builder in builders:
    sql = builder.get_criteria_sql(criteria)
    print(f"Generated SQL: {sql[:100]}...")
```

## Generated SQL Examples

### Condition Occurrence SQL
```sql
-- Begin Condition Occurrence Criteria
SELECT C.person_id, C.condition_occurrence_id as event_id, C.start_date, C.end_date,
  C.visit_occurrence_id, C.start_date as sort_date
FROM 
(
  SELECT co.person_id, co.condition_occurrence_id, co.condition_concept_id, co.visit_occurrence_id 
  FROM @cdm_database_schema.CONDITION_OCCURRENCE co
  
) C

-- End Condition Occurrence Criteria
```

### Drug Exposure SQL
```sql
-- Begin Drug Exposure Criteria
SELECT C.person_id, C.drug_exposure_id as event_id, C.drug_exposure_start_date, C.drug_exposure_end_date,
  C.visit_occurrence_id, C.drug_exposure_start_date as sort_date
FROM 
(
  SELECT de.person_id, de.drug_exposure_id, de.drug_concept_id, de.visit_occurrence_id 
  FROM @cdm_database_schema.DRUG_EXPOSURE de
  
) C

-- End Drug Exposure Criteria
```

## Java Equivalents

All Python builder classes have direct Java equivalents:

| Python Class | Java Equivalent |
|--------------|-----------------|
| `BuilderUtils` | `org.ohdsi.circe.cohortdefinition.builders.BuilderUtils` |
| `BuilderOptions` | `org.ohdsi.circe.cohortdefinition.builders.BuilderOptions` |
| `CriteriaColumn` | `org.ohdsi.circe.cohortdefinition.builders.CriteriaColumn` |
| `CriteriaSqlBuilder` | `org.ohdsi.circe.cohortdefinition.builders.CriteriaSqlBuilder` |
| `ConditionOccurrenceSqlBuilder` | `org.ohdsi.circe.cohortdefinition.builders.ConditionOccurrenceSqlBuilder` |
| `DrugExposureSqlBuilder` | `org.ohdsi.circe.cohortdefinition.builders.DrugExposureSqlBuilder` |
| `ProcedureOccurrenceSqlBuilder` | `org.ohdsi.circe.cohortdefinition.builders.ProcedureOccurrenceSqlBuilder` |

## Future Enhancements

The current implementation provides the foundation for SQL query generation. Future enhancements could include:

1. **Complete Implementation**: Implement all abstract methods with full Java logic
2. **Additional Builders**: Add builders for all OMOP CDM tables
3. **Criteria Classes**: Create specific criteria classes (ConditionOccurrence, DrugExposure, etc.)
4. **Advanced Features**: Support for complex criteria, nested queries, and advanced SQL features
5. **Validation**: Add SQL validation and error checking
6. **Performance**: Optimize SQL generation for large datasets

## Testing

All builders have been tested for:
- ✅ Successful import and instantiation
- ✅ SQL generation without errors
- ✅ Template placeholder replacement
- ✅ Column mapping functionality
- ✅ Builder options integration

The implementation provides a solid foundation for SQL query generation that mirrors the Java CIRCE-BE functionality.
"""
