---
description: Build OHDSI cohort definitions using the Pythonic context manager API
---

# Cohort Builder Skill

Build OHDSI cohort definitions using the `CohortBuilder` context manager.

**⚠️ AUTO-GENERATED**: This file is generated from the codebase. Do not edit manually.

## Basic Usage

```python
from circe.cohort_builder import CohortBuilder

with CohortBuilder("My Cohort") as cohort:
    cohort.with_condition(1)  # Entry event
    cohort.first_occurrence()
    cohort.require_drug(2, within_days_before=30)

expression = cohort.expression  # Access after context exits
```

## ⚠️ CRITICAL API NOTES

### 1. Use Context Manager (`with`) Block
- Cohort auto-builds when exiting the `with` block
- Access result via `.expression` property after exiting
- Do NOT call `.build()` - it's automatic

### 2. Demographic Methods Accept Multiple Values, NOT Lists

❌ **WRONG**:
```python
cohort.require_gender([8507, 8532])  # ERROR!
```

✅ **CORRECT**:
```python
cohort.require_gender(8507, 8532)  # Multiple values as separate arguments
```

### 3. Time Windows Use Keyword Arguments

```python
cohort.require_drug(2, within_days_before=30)
cohort.exclude_condition(3, anytime_before=True)
```

**Available time windows:**
- `within_days_before=N`
- `within_days_after=N`
- `anytime_before=True`
- `anytime_after=True`
- `same_day=True`
- `during_event=True`

## Entry Event Methods

Start with one entry event inside the context:

```python
cohort.with_condition(concept_set_id, kwargs)
cohort.with_condition_era(concept_set_id, kwargs)
cohort.with_death()
cohort.with_device_exposure(concept_set_id, kwargs)
cohort.with_dose_era(concept_set_id)
cohort.with_drug(concept_set_id, kwargs)
cohort.with_drug_era(concept_set_id, kwargs)
cohort.with_location_region(concept_set_id)
cohort.with_measurement(concept_set_id, kwargs)
cohort.with_observation(concept_set_id, kwargs)
cohort.with_observation_period()
cohort.with_observation_window(prior_days=0, post_days=0)
cohort.with_payer_plan_period(concept_set_id, kwargs)
cohort.with_procedure(concept_set_id, kwargs)
cohort.with_specimen(concept_set_id, kwargs)
cohort.with_visit(concept_set_id, kwargs)
cohort.with_visit_detail(concept_set_id)
```

## Entry Configuration Methods

```python
cohort.first_occurrence()                   # Only first occurrence per person
cohort.with_observation_window(prior_days=365, post_days=0)
cohort.min_age(18)                          # Minimum age at entry
cohort.max_age(65)                          # Maximum age at entry
```

## Demographic Criteria

```python
cohort.require_gender(8507, 8532)           # Multiple as separate args
cohort.require_race(8516)
cohort.require_ethnicity(38003563)
cohort.require_age(min_age=18, max_age=65)
```

## Inclusion/Exclusion Criteria

```python
cohort.require_condition(id, **time_window)
cohort.require_drug(id, **time_window)
cohort.require_procedure(id, **time_window)
cohort.require_measurement(id, **time_window)
cohort.exclude_condition(id, **time_window)
cohort.exclude_drug(id, **time_window)
```

## Named Inclusion Rules

Use nested context for named rules (for attrition tracking):

```python
with CohortBuilder("Complex Cohort") as cohort:
    cohort.with_condition(1)
    
    with cohort.include_rule("Prior Treatment") as rule:
        rule.require_drug(2, anytime_before=True)
    
    with cohort.include_rule("Lab Confirmation") as rule:
        rule.require_measurement(3, same_day=True)

expression = cohort.expression
```
