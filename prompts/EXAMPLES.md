# Validated Examples for Cohort Builder Prompts

**Note**: These examples use the context manager API and are guaranteed to execute successfully.

## ⚠️ CRITICAL API NOTES

### 1. Use Context Manager (`with`) Block

The context manager auto-builds the cohort on exit. Access the result via `.expression`:

```python
with CohortBuilder("My Cohort") as cohort:
    cohort.with_condition(1)
    cohort.require_drug(2, within_days_before=30)

expression = cohort.expression  # Built CohortExpression
```

### 2. Demographic Methods Accept Individual Values, NOT Lists

❌ **WRONG**:
```python
cohort.require_gender([8507, 8532])  # ERROR!
cohort.require_race([8516])           # ERROR!
```

✅ **CORRECT**:
```python
cohort.require_gender(8507, 8532)     # Multiple values unpacked
cohort.require_race(8516)             # Single value
cohort.require_ethnicity(38003563, 38003564)  # Multiple unpacked
```

### 3. Time Windows Use Keyword Arguments

Time windows are specified directly on criteria methods:

```python
cohort.require_drug(2, within_days_before=30)
cohort.exclude_condition(3, anytime_before=True)
cohort.require_measurement(4, same_day=True)
```

**Available time window parameters:**
- `within_days_before=N`
- `within_days_after=N`
- `anytime_before=True`
- `anytime_after=True`
- `same_day=True`
- `during_event=True`

---

## Example 1: Simple Age-Restricted Cohort

```python
from circe.cohort_builder import CohortBuilder

with CohortBuilder("Adults with Diabetes") as cohort:
    cohort.with_condition(1)
    cohort.require_age(min_age=18)

expression = cohort.expression
```

## Example 2: Incident (First-Time) Diagnosis

```python
from circe.cohort_builder import CohortBuilder

with CohortBuilder("New Diabetes Diagnosis") as cohort:
    cohort.with_condition(1)
    cohort.first_occurrence()
    cohort.with_observation_window(prior_days=365)
    cohort.min_age(18)

expression = cohort.expression
```

## Example 3: With Inclusion Criteria (Named Rule)

```python
from circe.cohort_builder import CohortBuilder

with CohortBuilder("Diabetes with Prior Metformin") as cohort:
    cohort.with_condition(1)
    cohort.first_occurrence()
    cohort.require_age(min_age=18, max_age=75)
    
    with cohort.include_rule("Prior Metformin Use") as rule:
        rule.require_drug(2, anytime_before=True)

expression = cohort.expression
```

## Example 4: With Exclusion Criteria

```python
from circe.cohort_builder import CohortBuilder

with CohortBuilder("Diabetes Without Prior Insulin") as cohort:
    cohort.with_condition(1)
    cohort.first_occurrence()
    
    with cohort.include_rule("No Prior Insulin") as rule:
        rule.exclude_drug(3, anytime_before=True)

expression = cohort.expression
```

## Example 5: Complex Multi-Criteria Cohort

```python
from circe.cohort_builder import CohortBuilder

with CohortBuilder("T2DM with Metformin and Lab") as cohort:
    cohort.with_condition(1)
    cohort.first_occurrence()
    cohort.with_observation_window(prior_days=365)
    cohort.require_age(min_age=18, max_age=75)
    
    with cohort.include_rule("Metformin Within 30 Days") as rule:
        rule.require_drug(2, within_days_after=30)
    
    with cohort.include_rule("HbA1c Within 180 Days") as rule:
        rule.require_measurement(4, within_days_after=180)
    
    with cohort.include_rule("No Prior Insulin") as rule:
        rule.exclude_drug(3, within_days_before=180)

expression = cohort.expression
```

## Example 6: Multiple Criteria in Same Rule

```python
from circe.cohort_builder import CohortBuilder

with CohortBuilder("Diabetes with Complications") as cohort:
    cohort.with_condition(1)
    cohort.first_occurrence()
    
    # Multiple criteria in same rule (all must be met)
    with cohort.include_rule("Has Complications and Treatment") as rule:
        rule.require_condition(10, same_day=True)  # Complication
        rule.require_drug(2, within_days_before=30)  # Treatment

expression = cohort.expression
```

---

**Key Patterns Demonstrated:**
1. Context manager auto-builds on exit
2. Access result via `.expression` property
3. Use `with cohort.include_rule("Name") as rule:` for named rules
4. Time windows as keyword arguments on criteria methods
5. Demographic restrictions via `require_gender()`, `require_age()`, etc.
