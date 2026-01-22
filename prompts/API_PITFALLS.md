# Common API Pitfalls and How to Avoid Them

This document clarifies common confusions with the Cohort Builder API.

## Issue 1: `require_gender()` and Other Demographic Methods

### ❌ WRONG - Passing a list
```python
.require_gender([8507, 8532])  # ERROR! Pydantic validation error
.require_race([8516, 8527])    # ERROR!
```

### ✅ CORRECT - Unpacking arguments
```python
.require_gender(8507, 8532)  # Male and Female
.require_race(8516, 8527)    # Multiple races
```

**Why?** These methods use `*concept_ids: int`, which means:
- They accept multiple individual integers: `.require_gender(8507, 8532, 8551)`
- They do NOT accept a list: `.require_gender([8507, 8532])`

**Solution for prompts:** Always show these methods with unpacked arguments, never with lists.

---

## Issue 2: Time Windows Are on Query Builders, Not CohortWithCriteria

### ❌ WRONG - Trying to chain time windows on CohortWithCriteria
```python
cohort = (
    CohortBuilder("Test")
    .with_condition(1)
    .anytime_after()  # ERROR! CohortWithCriteria doesn't have this
    .build()
)
```

### ✅ CORRECT - Time windows are on the query returned by require_* methods
```python
cohort = (
    CohortBuilder("Test")
    .with_condition(1)  # Entry event
    .require_drug(2).anytime_after()  # Time window on the query builder
    .build()
)
```

**Why?** The API structure is:
1. `CohortBuilder` → creates `CohortWithEntry`
2. `CohortWithEntry.with_condition()` → creates `CohortWithCriteria`
3. `CohortWithCriteria.require_drug()` → creates `DrugQuery`
4. `DrugQuery.anytime_after()` → returns `CohortWithCriteria`

**Time window methods (`.anytime_after()`, `.anytime_before()`, `.within_days_before()`, etc.) only exist on query builders, NOT on `CohortWithCriteria`.**

**Solution for prompts:** Make it crystal clear that:
- `.require_X()` methods return query builders
- Time windows are called ON those query builders
- After a time window, you're back to `CohortWithCriteria`

---

## Recommended Skill Updates

### 1. Always Use Named Parameters for Clarity

Even though the API accepts positional arguments, prompts should show named parameters:

```python
# SHOW THIS in prompts:
.require_gender(concept_ids=[8507, 8532])  # More explicit (if we add this parameter name)

# OR unpacked clearly:
.require_gender(8507, 8532)  # Multiple values, NOT a list
```

### 2. Emphasize Query Builder Pattern

Add a section to the skill explaining the chaining flow:

```
Entry → require_X() → Query Builder → time_window() → back to CohortWithCriteria
```

### 3. Update Examples to Never Show Lists for Demographic Methods

Replace:
```python
.require_gender([8507])
```

With:
```python
.require_gender(8507)  # Single value
.require_gender(8507, 8532)  # Multiple values
```
