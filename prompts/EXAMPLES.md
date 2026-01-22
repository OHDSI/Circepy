# Validated Examples for Cohort Builder Prompts

**Note**: These examples are extracted from working code in the `examples/` directory and are guaranteed to execute successfully.

## ⚠️ CRITICAL API NOTES

### 1. Demographic Methods Accept Individual Values, NOT Lists

❌ **WRONG**:
```python
.require_gender([8507, 8532])  # ERROR!
.require_race([8516])           # ERROR!
```

✅ **CORRECT**:
```python
.require_gender(8507, 8532)     # Multiple values unpacked
.require_race(8516)             # Single value
.require_ethnicity(38003563, 38003564)  # Multiple unpacked
```

### 2. Time Windows Are On Query Builders, Not CohortWithCriteria

❌ **WRONG**:
```python
.with_condition(1).anytime_after()  # ERROR! CohortWithCriteria has no time windows
```

✅ **CORRECT**:
```python
.with_condition(1)  # Returns CohortWithCriteria
.require_drug(2).anytime_after()  # .require_drug() returns DrugQuery which HAS time windows
```

**Key Rule**: Time window methods (`.anytime_before()`, `.within_days_after()`, etc.) only exist on **query builders** returned by `.require_X()` and `.exclude_X()` methods.

---

## Example 1: Simple Age-Restricted Cohort

Basic cohort with just an entry event and age restriction:

```python
from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("Adults with Diabetes")
    .with_condition(1)
    .require_age(18)
    .build()
)
```

## Example 2: Incident (First-Time) Diagnosis

Capturing only the first occurrence with observation window:

```python
from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("New Diabetes Diagnosis")
    .with_condition(1)
    .first_occurrence()
    .with_observation(prior_days=365)
    .min_age(18)
    .build()
)
```

## Example 3: With Inclusion Criteria

Entry event with prior medication requirement:

```python
from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("Diabetes with Prior Metformin")
    .with_condition(1)
    .first_occurrence()
    .require_age(18, 75)
    .begin_rule("Prior Metformin Use")
    .require_drug(2).anytime_before()
    .build()
)
```

## Example 4: With Exclusion Criteria

Using `.exclude_` methods:

```python
from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("Diabetes Without Prior Insulin")
    .with_condition(1)
    .first_occurrence()
    .begin_rule("No Prior Insulin")
    .exclude_drug(3).anytime_before()
    .build()
)
```

## Example 5: Complex Multi-Criteria Cohort

Multiple inclusion rules with different time windows:

```python
from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("T2DM with Metformin and Lab")
    .with_condition(1)
    .first_occurrence()
    .with_observation(prior_days=365)
    .require_age(18, 75)
    .begin_rule("Metformin Within 30 Days")
    .require_drug(2).within_days_after(30)
    .begin_rule("HbA1c Within 180 Days")
    .require_measurement(4).within_days_after(180)
    .begin_rule("No Prior Insulin")
    .exclude_drug(3).within_days_before(180)
    .build()
)
```

## Example 6: Using Collection Methods

**IMPORTANT**: Collection methods (`require_any_of`, `require_all_of`) work both with and without `begin_rule()`:

```python
from circe.cohort_builder import CohortBuilder

# Pattern 1: Without begin_rule (simpler)
cohort = (
    CohortBuilder("Diabetes with Complications")
    .with_condition(1)
    .first_occurrence()
    .require_any_of(condition_ids=[10, 11, 12])  # Retinopathy OR neuropathy OR nephropathy
    .build()
)

# Pattern 2: With begin_rule (for named rule/attrition)
cohort = (
    CohortBuilder("Diabetes with Complications")
    .with_condition(1)
    .first_occurrence()
    .begin_rule("At Least One Complication")  # Creates named inclusion rule
    .require_any_of(condition_ids=[10, 11, 12])  # Adds criteria to that rule
    .build()
)
```

## Example 7: Measurement with Modifiers

Domain-specific modifiers for measurements (remember: modifiers BEFORE time windows!):

```python
from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("High Glucose Readings")
    .with_measurement(1)
    .begin_rule("Abnormal HbA1c")
    .require_measurement(2)
        .with_operator(4172704)  # Greater than
        .with_value(min_val=6.5, max_val=15.0)
        .is_abnormal()
        .at_least(2)
        .within_days_before(365)  # Time window LAST
    .build()
)
```

---

**Key Patterns Demonstrated:**
1. Simple entry events
2. First occurrence filtering
3. Observation windows
4. Age restrictions
5. Inclusion/exclusion criteria with `.begin_rule()`
6. **Collection methods work with OR without `.begin_rule()`**
7. Time windows (before/after)
8. Domain-specific modifiers
9. Occurrence counting (at_least)
10. Multiple inclusion rules

**Critical Rules:**
- Modifiers (`.at_least`, `.with_value`, etc.) MUST come BEFORE time windows
- Collection methods (`.require_any_of`, `.require_all_of`) can be used directly OR after `.begin_rule()`
- `.begin_rule()` is optional - use it to create named rules for attrition tracking
