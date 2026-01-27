# API Pitfalls and Common Errors

**Updated for the context manager API.**

## ✅ Correct Pattern: Context Manager

Always use the `with` block pattern. The cohort auto-builds on exit:

```python
from circe.cohort_builder import CohortBuilder

# Correct usage
with CohortBuilder("My Cohort") as cohort:
    cohort.with_condition(1)
    cohort.require_drug(2, within_days_before=30)

expression = cohort.expression  # Access after exiting context
```

## ❌ Common Mistakes

### 1. Accessing `.expression` Inside the Context

```python
# WRONG - will raise RuntimeError
with CohortBuilder("Test") as cohort:
    cohort.with_condition(1)
    expr = cohort.expression  # ❌ ERROR! Still inside context
```

### 2. Forgetting to Define Entry Event

```python
# WRONG - no entry event defined
with CohortBuilder("Test") as cohort:
    pass  # No with_condition, with_drug, etc.

expr = cohort.expression  # ❌ RuntimeError: No cohort built
```

### 3. Using Lists for Demographic Methods

```python
# WRONG
cohort.require_gender([8507, 8532])  # ❌ Lists not supported

# CORRECT
cohort.require_gender(8507, 8532)  # ✅ Separate arguments
```

### 4. Missing `as` Variable for Nested Rules

```python
# WRONG - can't call methods on rule context
with cohort.include_rule("My Rule"):
    cohort.require_drug(2)  # Wrong object

# CORRECT
with cohort.include_rule("My Rule") as rule:
    rule.require_drug(2, anytime_before=True)  # ✅ Use rule variable
```

## State Transitions

1. `CohortBuilder` → defines title and concept sets
2. `with_*` methods → define entry event (required)
3. `require_*`, `exclude_*` → add inclusion/exclusion criteria
4. `include_rule()` → creates nested context for named rules
5. Exit `with` block → cohort auto-builds
6. `.expression` property → access built `CohortExpression`
