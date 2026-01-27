# Cohort Builder API Enhancements

## Summary

This document summarizes the enhancements made to the `circe.cohort_builder` fluent API to support advanced cohort definition features including nested criteria groups, demographic filters, and comprehensive OHDSI CIRCE parity.

## Key Features Added

### 1. Nested Criteria Groups

**Purpose**: Enable complex logical grouping of inclusion criteria (ANY, ALL, AT_LEAST)

**Implementation**:
- Added `GroupConfig` dataclass to represent nested criteria groups
- Implemented `CriteriaGroupBuilder` class for fluent nested group construction
- Added methods: `any_of()`, `all_of()`, `at_least_of(count)`, `end_group()`
- Updated `_build_criteria_group()` to recursively process nested groups

**Example**:
```python
from circe.cohort_builder import Cohort

cohort = (
    Cohort('Complex Cohort')
    .with_condition(1)
    .any_of()
        .require_drug(10).anytime_before()
        .all_of()
            .require_procedure(20).same_day()
            .require_measurement(30).anytime_after()
        .end_group()
    .end_group()
    .build()
)
```

### 2. Demographic Filters

**Purpose**: Filter cohort members by demographic attributes (age, gender, race, ethnicity)

**Implementation**:
- Extended `CohortSettings` with demographic fields:
  - `gender_concepts: List[int]`
  - `race_concepts: List[int]`
  - `ethnicity_concepts: List[int]`
  - `age_min: Optional[int]`
  - `age_max: Optional[int]`
- Added methods to `CohortWithEntry` and `CohortWithCriteria`:
  - `require_gender(*concept_ids)`
  - `require_race(*concept_ids)`
  - `require_ethnicity(*concept_ids)`
  - `require_age(min_age, max_age)`
- Automatic creation of `DemographicCriteria` inclusion rule

**Example**:
```python
cohort = (
    Cohort('Adults Only')
    .with_condition(1)
    .require_age(18, 65)
    .require_gender(8507)  # Male
    .build()
)
```

### 3. Named Inclusion Rules

**Purpose**: Support attrition tracking by naming inclusion rules

**Implementation**:
- Added `begin_rule(name: str)` method to start a new named rule
- Modified `CohortWithCriteria` to manage rules as list of dictionaries
- Each rule contains: `{"name": str, "group": GroupConfig}`

**Example**:
```python
cohort = (
    Cohort('Multi-Rule Cohort')
    .with_condition(1)
    .begin_rule('Age Criteria')
    .require_age(18, 65)
    .begin_rule('Drug Exposure')
    .require_drug(10).anytime_before()
    .build()
)
```

### 4. Advanced Query Filters

**Purpose**: Support comprehensive OHDSI filtering capabilities

**New QueryConfig Fields**:
- `gender_concepts: List[int]` - Filter by gender
- `visit_type_concepts: List[int]` - Filter by visit type
- `provider_specialty_concepts: List[int]` - Filter by provider specialty
- `source_concept_set_id: Optional[int]` - Filter by source concepts
- `restrict_visit: bool` - Restrict to same visit as index
- `ignore_observation_period: bool` - Ignore observation period constraints

**New BaseQuery Methods**:
- `with_gender(*concept_ids)`
- `with_visit_type(*concept_ids)`
- `with_provider_specialty(*concept_ids)`
- `with_source_concept(concept_set_id)`
- `restrict_to_visit()`
- `ignore_observation_period()`
- `relative_to_index_end()`
- `relative_to_event_end()`

**Example**:
```python
cohort = (
    Cohort('Inpatient Drug Exposure')
    .with_condition(1)
    .require_drug(10)
        .with_visit_type(9201)  # Inpatient
        .restrict_to_visit()
        .anytime_before()
    .build()
)
```

### 5. Time Window Enhancements

**Purpose**: Support relative time windows to index/event end dates

**Implementation**:
- Added `use_index_end: bool` to `TimeWindow`
- Added `use_event_end: bool` to `TimeWindow`
- Implemented `relative_to_index_end()` and `relative_to_event_end()` methods
- Correctly map these flags to `Window` model in `_build_correlated_criteria()`

### 6. Domain-Specific Filters

**Purpose**: Support domain-specific filtering (measurements, drug exposures, eras, etc.)

**Enhanced Mapping in `_config_to_criteria()`**:
- Measurement: `value_as_number` (value_min/max)
- DrugExposure: `days_supply`, `quantity`
- DrugEra/ConditionEra: `era_length`
- DoseEra: `dose`
- VisitOccurrence: `visit_length`
- VisitDetail: `visit_detail_length`
- ObservationPeriod: `period_length`
- Gender, visit type, provider specialty mapping
- Source concept mapping for all relevant domains

## Architecture Changes

### State Transitions

The API maintains the following state progression:
```
CohortBuilder (Cohort)
  ↓ with_*()
CohortWithEntry
  ↓ require_*() / exclude_*() / any_of() / all_of()
CohortWithCriteria | CriteriaGroupBuilder
  ↓ build() / end_group()
CohortExpression
```

### Key Classes

1. **CohortBuilder (alias: Cohort)**
   - Entry point for cohort definition
   - Sets entry event and title

2. **CohortWithEntry**
   - Configures observation windows
   - Sets demographic filters
   - Transitions to criteria state

3. **CohortWithCriteria**
   - Manages inclusion/exclusion rules
   - Supports nested groups
   - Builds final `CohortExpression`

4. **CriteriaGroupBuilder**
   - Manages nested criteria groups
   - Supports recursive nesting
   - Returns to parent on `end_group()`

5. **CohortSettings**
   - Stores cohort-wide configuration
   - Demographics, exit strategy, era collapse

6. **GroupConfig**
   - Represents a criteria group
   - Supports types: ALL, ANY, AT_LEAST, AT_MOST
   - Contains list of `CriteriaConfig` and nested `GroupConfig`

## Testing

All features have been tested with example cohorts demonstrating:
- Simple cohorts with single criteria
- Nested groups (ANY within ALL)
- Demographic filtering
- Named inclusion rules
- Advanced query filters
- Time window configurations

## Future Enhancements

Potential areas for future development:
1. Correlated criteria within groups
2. Date adjustment support
3. Censoring criteria
4. Custom era strategies
5. Additional domain-specific filters
6. Validation and error handling improvements

## API Compatibility

All changes maintain backward compatibility with existing code while adding new optional features. The API is designed to be:
- **LLM-friendly**: Clear method names and guided state transitions
- **Type-safe**: Proper type hints throughout
- **Fluent**: Method chaining for readable cohort definitions
- **CIRCE-compatible**: Generates valid OHDSI CIRCE JSON

## Files Modified

- `circe/cohort_builder/builder.py` - Core builder implementation
- `circe/cohort_builder/query_builder.py` - Query configuration and base query
- `circe/cohort_builder/__init__.py` - Public API exports
- `circe/cohortdefinition/criteria.py` - Criteria models (no changes needed)
- `circe/cohortdefinition/core.py` - Core models (no changes needed)
