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
from circe.cohort_builder import Cohort

cohort = (
    Cohort("Cohort Title")
    .with_condition(concept_set_id=1)  # Entry event
    .require_age(18, 65)  # Demographics
    .require_drug(2).anytime_before()  # Inclusion criteria
    .build()
)
```

## API Reference

### Step 1: Start with Entry Event

```python
Cohort("Title")
    .with_condition(concept_set_id=N)      # Condition occurrence
    .with_condition_era(concept_set_id=N)  # Condition era
    .with_drug(concept_set_id=N)           # Drug exposure
    .with_drug_era(concept_set_id=N)       # Drug era
    .with_dose_era(concept_set_id=N)       # Dose era
    .with_procedure(concept_set_id=N)      # Procedure
    .with_measurement(concept_set_id=N)    # Measurement
    .with_visit(concept_set_id=N)          # Visit occurrence
    .with_visit_detail(concept_set_id=N)   # Visit detail
    .with_observation(concept_set_id=N)    # Observation
    .with_device_exposure(concept_set_id=N) # Device exposure
    .with_specimen(concept_set_id=N)       # Specimen
    .with_death(concept_set_id=N)          # Death
    .with_observation_period(concept_set_id=N)  # Observation period
    .with_payer_plan_period(concept_set_id=N)   # Payer plan period
    .with_location_region(concept_set_id=N)     # Location/region
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
    .begin_rule("Another Rule")   # Start another rule
    .require_procedure(N).same_day()
```

### Step 5: Add Nested Criteria Groups (Optional)

```python
    .any_of()                     # Start ANY group (OR logic)
        .require_drug(10).anytime_before()
        .require_procedure(20).same_day()
    .end_group()                  # End group
    
    .all_of()                     # Start ALL group (AND logic)
        .require_measurement(30).anytime_after()
        .require_visit(40).within_days_before(30)
    .end_group()
    
    .at_least_of(2)              # At least N criteria must match
        .require_drug(10).anytime_before()
        .require_drug(11).anytime_before()
        .require_drug(12).anytime_before()
    .end_group()
```

### Step 6: Add Simple Inclusion Criteria (Optional)

```python
    .require_condition(N).within_days_before(365)
    .require_drug(N).within_days_after(30)
    .require_measurement(N).same_day()
```

### Step 7: Add Exclusion Criteria (Optional)

```python
    .exclude_condition(N).anytime_before()
    .exclude_drug(N).within_days_before(365)
```

### Step 8: Add Censoring Events (Optional)

Censoring events cause a patient to exit the cohort if they occur after the entry date.

```python
    .censor_on_condition(N).anytime_after()
    .censor_on_drug(N).anytime_after()
    .censor_on_death().anytime_after()
```

### Step 9: Build
```python
    .build()  # Returns CohortExpression
```

## Time Window Options

| Method | Description |
|--------|-------------|
| `.within_days_before(N)` | N days before index |
| `.within_days_after(N)` | N days after index |
| `.within_days(before=N, after=M)` | Window around index |
| `.anytime_before()` | Any time before index |
| `.anytime_after()` | Any time after index |
| `.same_day()` | Same day as index |

## Advanced Query Filters

All query methods (`.require_*()`, `.exclude_*()`) support these filters:

### Occurrence Counting
```python
    .require_drug(N)
        .at_least(2)              # At least 2 occurrences
        .at_most(5)               # At most 5 occurrences
        .exactly(1)               # Exactly 1 occurrence
        .anytime_before()
```

### Age Filtering
```python
    .require_drug(N)
        .with_age(min_age=30, max_age=50)  # Age at event
        .anytime_before()
```

### Visit Constraints
```python
    .require_procedure(N)
        .with_visit_type(9201)    # Inpatient visits only
        .restrict_to_visit()      # Same visit as index event
        .same_day()
```

### Provider Specialty
```python
    .require_procedure(N)
        .with_provider_specialty(38004446)  # Cardiologist
        .anytime_before()
```

### Gender Filtering
```python
    .require_condition(N)
        .with_gender(8507)        # Male patients only
        .anytime_before()
```

### Source Concepts
```python
    .require_condition(N)
        .with_source_concept(concept_set_id=5)
        .anytime_before()
```

### Observation Period
```python
    .require_drug(N)
        .ignore_observation_period()  # Don't restrict to obs period
        .anytime_before()
```

### Time Window Modifiers
```python
    .require_drug(N)
        .relative_to_index_end()  # Relative to index event end date
        .within_days_after(30)
    
    .require_procedure(N)
        .relative_to_event_end()  # Relative to criteria event end date
        .within_days_before(7)
```

### Date Adjustment (Event Offsets)
```python
    .require_drug(N)
        .with_start_date_adjustment(-7) # Event starts 7 days before record start
        .with_end_date_adjustment(7)    # Event ends 7 days after record end
        .anytime_before()
```

### Advanced Measurement / Drug / Era Filters
```python
    .require_measurement(N)
        .with_unit(8505)                # Milligrams
        .is_abnormal()                  # Abnormal flag
        .with_value(10, 20)             # Numeric range
        .with_value_as_concept(4587)    # Concept result
        .anytime_before()
    
    .require_drug_era(N)
        .with_gap_days(0, 30)           # Era gap
        .with_occurrence_count(2)       # Number of events in era
        .anytime_before()
```

### Custom Era Exit Strategy
```python
    .with_condition(1)
    .exit_at_era_end(concept_set_id=10, gap_days=30, offset=0)
    .build()
```

### Correlated Criteria (Criteria within Criteria)

Apply criteria that must be met relative to a specific event.

```python
    .require_drug(10)           # Main event
        .with_all()             # Relational criteria (ALL must match)
            .require_procedure(20).same_day()
            .require_condition(30).within_days_before(30)
        .end_group()            # End relational group
        .anytime_before()       # Back to main event window
```

## Complete Examples

### Example 1: Simple Cohort with Demographics

```python
from circe.cohort_builder import Cohort

cohort = (
    Cohort("Adult Males with T2DM")
    .with_condition(1)  # T2DM diagnosis
    .require_age(18, 65)
    .require_gender(8507)  # Male
    .build()
)
```

### Example 2: Nested Groups with Complex Logic

```python
cohort = (
    Cohort("Complex Medication Cohort")
    .with_drug(1)  # Entry: Drug A
    .first_occurrence()
    .require_age(18)
    .any_of()  # Patient must have EITHER:
        .require_drug(2).at_least(2).anytime_before()  # 2+ exposures to Drug B
        .all_of()  # OR BOTH:
            .require_procedure(10).same_day()  # Procedure on same day
            .require_measurement(20).within_days_before(30)  # Recent measurement
        .end_group()
    .end_group()
    .build()
)
```

### Example 3: Named Inclusion Rules for Attrition

```python
cohort = (
    Cohort("Metformin Users with Attrition")
    .with_drug(1)  # Metformin
    .first_occurrence()
    .begin_rule("Age Criteria")
    .require_age(18, 65)
    .begin_rule("Prior Diagnosis")
    .require_condition(2).within_days_before(365)  # T2DM in prior year
    .begin_rule("No Prior Insulin")
    .exclude_drug(3).anytime_before()  # No insulin before
    .build()
)
```

### Example 4: Advanced Filters

```python
cohort = (
    Cohort("Inpatient Procedures")
    .with_procedure(1)
    .require_age(18)
    .require_procedure(2)
        .with_visit_type(9201)  # Inpatient only
        .with_provider_specialty(38004446)  # Cardiologist
        .restrict_to_visit()  # Same visit as index
        .same_day()
    .build()
)
```

### Example 5: Complete Real-World Example

```python
from circe.cohort_builder import Cohort
from circe.vocabulary import concept_set, descendants

# Define concept sets
t2dm = concept_set(descendants(201826), id=1, name="T2DM")
metformin = concept_set(descendants(1503297), id=2, name="Metformin")
insulin = concept_set(descendants(1511348), id=3, name="Insulin")
a1c = concept_set(descendants(3004410), id=4, name="HbA1c")

# Build cohort
cohort = (
    Cohort("New Metformin Users with T2DM")
    .with_concept_sets(t2dm, metformin, insulin, a1c)
    .with_drug(2)  # Entry: Metformin exposure
    .first_occurrence()
    .with_observation(prior_days=365)
    .require_age(18, 75)
    .require_gender(8507, 8532)  # Male or Female
    .begin_rule("T2DM Diagnosis")
    .require_condition(1).within_days_before(365)
    .begin_rule("No Prior Insulin")
    .exclude_drug(3).anytime_before()
    .begin_rule("Recent A1C")
    .require_measurement(4).within_days_before(90)
    .build()
)
```

## Common Patterns

### First-Ever Diagnosis
```python
(Cohort("First T2DM Diagnosis")
    .with_condition(1)
    .first_occurrence()
    .with_observation(prior_days=365)
    .exclude_condition(1).anytime_before()
    .build())
```

### New Drug User
```python
(Cohort("New Metformin Users")
    .with_drug(2)
    .first_occurrence()
    .with_observation(prior_days=365)
    .exclude_drug(2).within_days_before(365)
    .build())
```

### Disease + Treatment
```python
(Cohort("T2DM on Metformin")
    .with_drug(2)
    .first_occurrence()
    .require_condition(1).within_days_before(365)
    .build())
```

### Complex Nested Logic
```python
(Cohort("Complex Criteria")
    .with_condition(1)
    .all_of()  # Must have ALL of:
        .require_drug(10).anytime_before()
        .any_of()  # AND at least ONE of:
            .require_procedure(20).same_day()
            .require_measurement(30).within_days_before(30)
        .end_group()
    .end_group()
    .build())
```

## Implementation Status

### ✅ Fully Implemented Features

**Entry Events (All OMOP Domains):**
- ✅ Condition Occurrence
- ✅ Condition Era
- ✅ Drug Exposure
- ✅ Drug Era
- ✅ Dose Era
- ✅ Procedure Occurrence
- ✅ Measurement
- ✅ Visit Occurrence
- ✅ Visit Detail
- ✅ Observation
- ✅ Device Exposure
- ✅ Specimen
- ✅ Death
- ✅ Observation Period
- ✅ Payer Plan Period
- ✅ Location Region
- ✅ Censoring Events (`censor_on_*`)

**Criteria Methods:**
- ✅ All `require_*()` methods for all domains
- ✅ All `exclude_*()` methods for all domains

**Demographics:**
- ✅ Age filtering (`require_age()`)
- ✅ Gender filtering (`require_gender()`)
- ✅ Race filtering (`require_race()`)
- ✅ Ethnicity filtering (`require_ethnicity()`)

**Nested Groups:**
- ✅ `any_of()` - OR logic
- ✅ `all_of()` - AND logic
- ✅ `at_least_of(N)` - At least N criteria
- ✅ Recursive nesting (groups within groups)
- ✅ `end_group()` to close groups

**Named Inclusion Rules:**
- ✅ `begin_rule(name)` - Start named rule for attrition tracking

**Occurrence Counting:**
- ✅ `at_least(N)` - At least N occurrences
- ✅ `at_most(N)` - At most N occurrences
- ✅ `exactly(N)` - Exactly N occurrences

**Advanced Filters:**
- ✅ `with_age(min, max)` - Age at event
- ✅ `with_gender(*ids)` - Gender filtering
- ✅ `with_visit_type(*ids)` - Visit type filtering
- ✅ `with_provider_specialty(*ids)` - Provider specialty
- ✅ `with_source_concept(id)` - Source concept filtering
- ✅ `restrict_to_visit()` - Same visit as index
- ✅ `ignore_observation_period()` - Ignore obs period
- ✅ `relative_to_index_end()` - Time relative to index end
- ✅ `relative_to_event_end()` - Time relative to event end
- ✅ `with_all()`, `with_any()`, `with_at_least()` - Correlated criteria

**Entry Configuration:**
- ✅ `first_occurrence()` / `all_occurrences()`
- ✅ `with_observation(prior_days, post_days)`
- ✅ `min_age(age)` / `max_age(age)`
- ✅ `exit_at_observation_end()` / `exit_after_days(days)`
- ✅ `collapse_era(days)`
- ✅ `with_start_date_adjustment()`, `with_end_date_adjustment()`
- ✅ `with_unit()`, `with_value_as_concept()`, `is_abnormal()`
- ✅ `with_gap_days()`, `with_occurrence_count()`
- ✅ `exit_at_era_end()` - Custom Era exit strategy

## When to Use Alternatives

### Use **Raw Pydantic Models** if you need:
- Custom SQL Extensions
- Custom extensions or experimental features

## Notes

- Concept set IDs must match IDs in your concept sets
- Call `.build()` to get the final `CohortExpression`
- Use `build_cohort_query(cohort)` to generate SQL
- All features are fully compatible with OHDSI CIRCE specification
- The API is designed to be LLM-friendly with clear state transitions
