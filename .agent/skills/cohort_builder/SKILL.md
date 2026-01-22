---
description: Build OHDSI cohort definitions using the fluent Python API
---

# Cohort Builder Skill

Build OHDSI cohort definitions step-by-step using the fluent `cohort_builder` API.

**⚠️ AUTO-GENERATED**: This file is generated from the codebase. Do not edit manually.

## ⚠️ CRITICAL API NOTES

### 1. Demographic Methods Accept Multiple Values, NOT Lists

❌ **WRONG**:
```python
.require_gender([8507, 8532])  # ERROR! Pydantic validation error
.require_race([8516])           # ERROR!
```

✅ **CORRECT**:
```python
.require_gender(8507, 8532)     # Multiple values as separate arguments
.require_race(8516)             # Single value
.require_ethnicity(38003563, 38003564)  # Multiple values unpacked
```

### 2. Time Windows Are ONLY on Query Builders

Time window methods (`.anytime_before()`, `.within_days_after()`, etc.) exist ONLY on query builders returned by `.require_X()` and `.exclude_X()` methods.

❌ **WRONG**:
```python
.with_condition(1).anytime_after()  # ERROR! CohortWithCriteria has no time windows
```

✅ **CORRECT**:
```python
.with_condition(1)              # Returns CohortWithCriteria
.require_drug(2).anytime_after()  # .require_drug() returns DrugQuery (has time windows!)
```

**API Flow**: `CohortWithCriteria.require_X()` → `QueryBuilder` (with time windows) → `.time_window()` → back to `CohortWithCriteria`

## Entry Event Methods

Start building a cohort with one of these methods on `CohortBuilder`:

```python
CohortBuilder("Title").with_condition(concept_set_id, kwargs)
CohortBuilder("Title").with_condition_era(concept_set_id, kwargs)
CohortBuilder("Title").with_death()
CohortBuilder("Title").with_device_exposure(concept_set_id, kwargs)
CohortBuilder("Title").with_dose_era(concept_set_id)
CohortBuilder("Title").with_drug(concept_set_id, kwargs)
CohortBuilder("Title").with_drug_era(concept_set_id, kwargs)
CohortBuilder("Title").with_location_region(concept_set_id)
CohortBuilder("Title").with_measurement(concept_set_id, kwargs)
CohortBuilder("Title").with_observation(concept_set_id, kwargs)
CohortBuilder("Title").with_observation_period()
CohortBuilder("Title").with_payer_plan_period(concept_set_id, kwargs)
CohortBuilder("Title").with_procedure(concept_set_id, kwargs)
CohortBuilder("Title").with_specimen(concept_set_id, kwargs)
CohortBuilder("Title").with_visit(concept_set_id, kwargs)
CohortBuilder("Title").with_visit_detail(concept_set_id)
```

## Entry Configuration Methods

After defining the entry event, configure it with:

### `.first_occurrence()`
Only use the first occurrence per person for entry events.

### `.max_age(age)`
Require maximum age at entry for all entry events.

### `.min_age(age)`
Require minimum age at entry for all entry events.

### `.with_observation(prior_days=0, post_days=0)`
Set continuous observation requirements.

Args:
    prior_days: Days of observation required before index
    post_days: Days of observation required after index
    
Returns:
    Self for chaining

## Demographic Criteria

Add demographic requirements:

- `.require_age(min_age, max_age)`: Require specific age range
- `.require_ethnicity(concept_ids)`: Require specific ethnicity concept IDs
- `.require_gender(concept_ids)`: Require specific gender concept IDs
- `.require_race(concept_ids)`: Require specific race concept IDs

## ⚠️ CRITICAL CHAINING RULE

**Modifiers MUST be called BEFORE time windows!**

Time window methods finalize the criteria and return to the parent builder.
Once a time window is called, you cannot chain further modifiers.

✅ **CORRECT**:
```python
.require_drug(10).at_least(2).within_days_before(30)
```

❌ **INCORRECT**:
```python
.require_drug(10).within_days_before(30).at_least(2)  # ERROR!
```

## Time Window Methods (Call LAST)

These methods finalize the criteria:

- `.anytime_after()`: Events occurring any time after the index
- `.anytime_before()`: Events occurring any time before the index
- `.before_event_end(days=0)`: Events occurring before the end of the index event
- `.during_event()`: Events occurring within the duration of the index event
- `.restrict_to_visit()`: Restrict criteria to the same visit as the index event
- `.same_day()`: Events occurring on the same day as the index
- `.within_days(before=0, after=0)`: Events occurring within a window of [before, after] days
- `.within_days_after(days)`: Events occurring within N days after the index
- `.within_days_before(days)`: Events occurring within N days before the index

## Modifier Methods (Call BEFORE time windows)

### BaseQuery

- `.at_least(count)`
- `.at_most(count)`
- `.exactly(count)`
- `.ignore_observation_period()`
- `.with_distinct()`

### ProcedureQuery

- `.with_modifier(concept_ids)`
- `.with_quantity(min_qty, max_qty)`

### MeasurementQuery

- `.is_abnormal(value=True)`
- `.with_operator(concept_ids)`
- `.with_range_high_ratio(min_ratio, max_ratio)`
- `.with_range_low_ratio(min_ratio, max_ratio)`
- `.with_unit(concept_ids)`
- `.with_value(min_val, max_val)`

### DrugQuery

- `.with_days_supply(min_days, max_days)`
- `.with_dose(min_dose, max_dose)`
- `.with_quantity(min_qty, max_qty)`
- `.with_refills(min_refills, max_refills)`
- `.with_route(concept_ids)`

### VisitQuery

- `.with_length(min_days, max_days)`
- `.with_place_of_service(concept_ids)`

### ObservationQuery

- `.with_qualifier(concept_ids)`
- `.with_value_as_string(value)`

## Inclusion Criteria Methods

Build complex criteria with:

### `.exclude_any_of(condition_ids, drug_ids, drug_era_ids, procedure_ids, measurement_ids, observation_ids, visit_ids)`
Exclude if ANY of the specified criteria are present.

This creates exclusion criteria with OR logic.

Args:
    condition_ids: List of condition concept set IDs to exclude
    drug_ids: List of drug ...

### `.require_all_of(condition_ids, drug_ids, drug_era_ids, procedure_ids, measurement_ids, observation_ids, visit_ids)`
Require ALL of the specified criteria (AND logic).

This is a shortcut for creating an ALL group with multiple criteria.

Args:
    condition_ids: List of condition concept set IDs
    drug_ids: List ...

### `.require_any_of(condition_ids, drug_ids, drug_era_ids, procedure_ids, measurement_ids, observation_ids, visit_ids)`
Require ANY of the specified criteria (OR logic).

This is a shortcut for creating an ANY group with multiple criteria
without manually chaining .any_of()...end_group().

Args:
    condition_ids: List...

### `.require_at_least_of(count, condition_ids, drug_ids, drug_era_ids, procedure_ids, measurement_ids, observation_ids, visit_ids)`
Require at least N of the specified criteria.

This is a shortcut for creating an AT_LEAST group.

Args:
    count: Minimum number of criteria that must be met
    condition_ids: List of condition con...
