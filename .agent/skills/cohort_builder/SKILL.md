---
description: Build OHDSI cohort definitions using the fluent Python API
---

# Cohort Builder Skill

Build OHDSI cohort definitions step-by-step using the fluent `cohort_builder` API.

## When to Use

Use this skill when the user wants to:
- Create a new cohort definition
- Define patient populations based on conditions, drugs, procedures, etc.
- Build inclusion/exclusion criteria with complex logic
- Apply demographic filters (age, gender, race, ethnicity)
- Create nested criteria groups (ANY/ALL logic)

## Quick Start

```python
from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("Cohort Title")
    .with_condition(concept_set_id=1)  # Entry event
    .require_age(18, 65)  # Demographics
    .build()
)
```

## API Reference

### Step 1: Start with Entry Event

```python
CohortBuilder("Title")
    .with_condition(concept_set_id=N)      # Condition occurrence
    .with_condition_era(concept_set_id=N)  # Condition era
    .with_drug(concept_set_id=N)           # Drug exposure
    .with_drug_era(concept_set_id=N)       # Drug era
    .with_dose_era(concept_set_id=N)       # Dose era
    .with_procedure(concept_set_id=N)      # Procedure
    .with_measurement(concept_set_id=N)    # Measurement
    .with_visit(concept_set_id=N)          # Visit occurrence
    .with_observation_period()             # Observation period (no arguments)
```

### Step 2: Configure Entry (Optional)

```python
    .first_occurrence()           # Only first event per person
    .with_observation(prior_days=365, post_days=0)  # Observation window
    .min_age(18)                  # Minimum age at event
    .max_age(65)                  # Maximum age at event
```

### Step 3: Add Demographics (Optional)

```python
    .require_age(min_age=18, max_age=65)  # Age range
    .require_gender(8507)                  # Gender (male=8507, female=8532)
    .require_race(8516)                    # Race concept IDs
    .require_ethnicity(38003564)           # Ethnicity concept IDs
```

### Step 4: Add Named Inclusion Rules (Optional)

```python
    .begin_rule("Rule Name")      # Start a named inclusion rule
    .require_drug(N).anytime_before()
```

### Step 5: Add Inclusion Criteria

#### Option A: Collection Methods (RECOMMENDED)

Simplified syntax for common patterns:

```python
# ANY of (OR logic) - patient must have at least one
.require_any_of(drug_ids=[10, 11, 12])

# ALL of (AND logic) - patient must have all
.require_all_of(measurement_ids=[40, 41])

# Exclusions
.exclude_any_of(condition_ids=[70, 71, 72])
```

#### Option B: Manual Nested Groups

```python
    .any_of()                     # Start ANY group (OR logic)
        .require_drug(10).anytime_before()
        .require_procedure(20).same_day()
    .end_group()                  # End group
```

### STEP 6: CRITICAL CHAINING RULE

**IMPORTANT**: Modality methods (count, qualifiers) MUST be called BEFORE time window methods. Time window methods finalize the criteria and return to the parent builder.

**CORRECT**:
```python
.require_drug(10).at_least(2).within_days_before(30)
```

**INCORRECT**:
```python
.require_drug(10).within_days_before(30).at_least(2)  # ERROR: at_least not found on CohortWithCriteria
```

## Modifiers and Modalities

### Occurrence Counting (Call BEFORE time window)

```python
.at_least(3)
.at_most(5)
.exactly(2)
.with_distinct()
```

### Time Windows (Finalizes criteria)

| Method | Description |
|--------|-------------|
| `.within_days_before(N)` | N days before index |
| `.within_days_after(N)` | N days after index |
| `.within_days(before=N, after=M)` | Window around index |
| `.anytime_before()` | Any time before index |
| `.anytime_after()` | Any time after index |
| `.same_day()` | Same day as index |
| `.restrict_to_visit()` | Same visit as index |
| `.during_event()` | Within index event duration |

## Domain-Specific Modifiers (Call BEFORE time window)

### Procedure Modifiers
```python
.require_procedure(N).with_quantity(1, 5).with_modifier(4184637).anytime_before()
```

### Measurement Modifiers
```python
.require_measurement(N).with_operator(4172704).with_value(10, 50).is_abnormal().anytime_before()
```

### Drug Modifiers
```python
.require_drug(N).with_route(4132161).with_dose(10, 50).anytime_before()
```

## Example: Secondary Primary Malignancy

```python
cohort = (
    CohortBuilder("Secondary Primary Malignancy")
    .with_condition(1)
    .first_occurrence()
    .with_observation(prior_days=365)
    .require_age(18, 85)
    
    .begin_rule("Second Primary Cancer at Different Site")
    .all_of()
        .require_condition(2).at_least(1).anytime_after()
        .any_of()
            .require_condition(10).anytime_after()
            .require_condition(11).anytime_after()
        .end_group()
    .end_group()
    
    .begin_rule("Time Gap Requirement")
    .require_condition(2).with_distinct().within_days_after(365)
    
    .begin_rule("No Metastatic Disease")
    .exclude_any_of(condition_ids=[100, 101, 102, 103])
    
    .begin_rule("Diagnostic Confirmation")
    .at_least_of(1)
        .require_procedure(200).with_modifier(4184637).within_days_after(0)
        .require_measurement(300).with_operator(4172704).with_distinct().at_least(2).anytime_after()
    .end_group()
    
    .build()
)
```
