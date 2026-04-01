---
description: Build phenotype evaluation rubrics using the Pythonic EvaluationBuilder API
---

# Evaluation Builder Skill

Build phenotype evaluation rubrics (collections of weighted rules) using the `EvaluationBuilder` context manager.

## Key Principles

1.  **Use named rules** - Each rule should have a clear, human-readable name reflecting its clinical meaning.
2.  **Weighted Evidence** - Assign weights to rules based on their importance in the phenotype definition.
3.  **Signed Weights for Polarity** - Use a positive `weight` for evidence of the phenotype and a negative `weight` for evidence against it (exclusions).
4.  **Complex Logic** - Use nested logical groups (`any_of`, `all_of`, `at_least_of`) for sophisticated rules that require multiple criteria.

## What Makes Good Evaluation Criteria

Unlike cohort definitions which are designed to *select* a population, evaluation rubrics are designed to *characterize* a pre-selected population.

- **Sensitivity vs. Specificity**: Criteria can be much broader than cohort entry events. You might include rules for "Any Measurement" of a lab even if the value is missing, as the mere presence of the test can be a signal of clinical interest.
- **Handling Missing Values**: It is often useful to have two rules: one for the "Presence of Measurement" (low weight) and another for the "Measurement with Elevated Value" (high weight).
- **Redundant Signs**: Include multiple ways a phenotype might manifest (ICD codes, specific drugs, lab results) to build a robust score.

## Expected Output

The `EvaluationQueryBuilder` generates SQL that calculates scores for every person in your index events across every rule in the rubric.

### Output Table: `cohort_rubric`
Results are inserted into a table named `cohort_rubric` (configurable) with the following structure:

| Column | Type | Description |
| :--- | :--- | :--- |
| `ruleset_id` | `INT` | Unique ID for this evaluation run/rubric |
| `subject_id` | `BIGINT` | The OMOP `person_id` being evaluated |
| `index_date` | `DATE` | The specific date the evaluation is anchored to |
| `rule_id` | `INT` | ID of the rule being scored |
| `score` | `FLOAT` | The calculated score (signed `weight`) or `0` if not matched |

> [!NOTE]
> This normalized format allows you to easily aggregate scores to get a total phenotype probability or analyze which specific rules are most frequently matching.

## Basic Pattern

```python
from circe.evaluation.builder import EvaluationBuilder

def create_gi_bleed_rubric():
    """Create an evaluation rubric for Gastrointestinal Bleeding."""
    
    with EvaluationBuilder("GI Bleed Evaluation") as ev:
        # 1. Define Concept Sets
        bleed = ev.concept_set("GI Bleed", 192671)
        aspirin = ev.concept_set("Aspirin", 1112807)
        
        # 2. Simple Rule (positive evidence)
        ev.add_rule("GI Bleed Diagnosis", weight=10).condition(bleed).at_least(1)
        
        # 3. Complex Rule with Temporal Window
        with ev.rule("Recent Aspirin Use", weight=5) as rule:
            rule.drug(aspirin).at_least(1).within_days_before(30)
            
        # 4. Exclusion Rule (negative weight means evidence AGAINST the phenotype)
        ev.add_rule("Alternative Diagnosis", weight=-5).condition(4329041)
        
    return ev.rubric
```

## API Reference

### Context Manager

```python
with EvaluationBuilder("Title") as ev:
    # Define rubric inside block
    ev.add_rule("Rule Name", weight=10).condition(123)

rubric = ev.rubric  # Access after block exits
```

### Rule Configuration

```python
ev.add_rule(name, weight, category=None)
```

-   `weight`: The numeric score assigned if the rule is matched. Positive values indicate supporting evidence; negative values indicate exclusions.
-   `category`: Optional grouping (e.g., "Primary", "Validation").

### Criteria Types

Rules support standard OMOP domains:

```python
rule.condition(concept_set_id)
rule.drug(concept_set_id)
rule.procedure(concept_set_id)
rule.measurement(concept_set_id)
rule.observation(concept_set_id)
rule.visit(concept_set_id)
rule.death(concept_set_id)
rule.condition_era(concept_set_id)
rule.drug_era(concept_set_id)
rule.device_exposure(concept_set_id)
```

### Criteria Modifiers (chained after a domain method)

These modify the **last criterion** added to the rule. They ONLY work on `RuleBuilder`, NOT inside group builders like `any_of()`.

```python
# Occurrence count (applied to the last criterion)
rule.condition(cs_id).at_least(2)     # At least 2 occurrences
rule.condition(cs_id).at_most(0)      # Zero occurrences (absence)

rule.within_days(before=N, after=M) # Asymmetric window allowed
rule.within_days(before=0, after=0) # On the index date only
rule.anytime_before()               # Any time before index - equivalent to rule.within_days(before = 99999, after = 0)
rule.anytime_after()                # Any time after index - equivalent to rule.within_days(before = 0, after = 99999)


# Chaining occurrence + time window
rule.condition(cs_id).at_least(1).within_days(before=365)

# Value ranges (Measurements)
rule.measurement(id).with_value(gt=130)
rule.measurement(id).with_value(between=(6.0, 6.4))
```

### Exclude Methods (shorthand for "exactly 0 occurrences")

Use `exclude_*` to assert the **absence** of a criterion. These are shorthand for adding
a criterion with exactly 0 occurrences and an optional time window.

```python
# Exclude if condition present any time before index
rule.exclude_condition(cs_id, anytime_before=True)

# Exclude if drug present within 365 days before
rule.exclude_drug(cs_id, within_days_before=365)

# All supported exclude methods:
rule.exclude_condition(cs_id, **time_window_kwargs)
rule.exclude_drug(cs_id, **time_window_kwargs)
rule.exclude_drug_era(cs_id, **time_window_kwargs)
rule.exclude_measurement(cs_id, **time_window_kwargs)
rule.exclude_procedure(cs_id, **time_window_kwargs)
rule.exclude_visit(cs_id, **time_window_kwargs)
rule.exclude_observation(cs_id, **time_window_kwargs)
rule.exclude_device_exposure(cs_id, **time_window_kwargs)
rule.exclude_condition_era(cs_id, **time_window_kwargs)
```

**Time window kwargs for exclude methods:**
- `anytime_before=True`
- `anytime_after=True`
- `within_days_before=N`
- `within_days_after=N`
- `same_day=True`

### Logical Grouping (Nested Criteria)

For rules requiring multiple criteria combined with logic operators, use group builders.

> [!IMPORTANT]
> Inside a group (`any_of`, `all_of`, `at_least_of`), use the **parameter-based** API
> (keyword arguments like `at_least=N`, `within_days_before=N`) instead of chaining
> methods like `.at_least(N)`. The group builder methods (`condition()`, `drug()`, etc.)
> accept kwargs and finalize in one call.

#### `any_of()` — OR logic (match at least one)

```python
with ev.rule("Any Supporting Evidence", weight=5) as rule:
    with rule.any_of() as group:
        group.condition(cs_dx)                                 # Has diagnosis
        group.drug(cs_drug, within_days_before=30)             # OR has drug within 30 days
        group.measurement(cs_lab, within_days_before=7)        # OR has lab within 7 days
```

#### `all_of()` — AND logic (must match all)

```python
with ev.rule("Confirmed Diagnosis", weight=10) as rule:
    with rule.all_of() as group:
        group.condition(cs_dx)                                 # Has diagnosis
        group.procedure(cs_biopsy, within_days_after=30)       # AND has biopsy after
```

#### `at_least_of(N)` — Match at least N of the criteria

```python
with ev.rule("Strong Evidence (2 of 3)", weight=8) as rule:
    with rule.at_least_of(2) as group:
        group.condition(cs_dx, at_least=1)
        group.drug(cs_drug, within_days_before=90)
        group.measurement(cs_lab, within_days_before=30)
```

#### `at_most_of(N)` — Match at most N of the criteria

```python
with ev.rule("Rare Side Effect", weight=-3) as rule:
    with rule.at_most_of(1) as group:
        group.condition(cs_side_effect_a)
        group.condition(cs_side_effect_b)
```

#### Nested Groups (complex logic trees)

Groups can be nested to build arbitrarily complex logic:

```python
with ev.rule("Complex Evidence", weight=10) as rule:
    with rule.all_of() as outer:
        # Must have the diagnosis
        outer.condition(cs_dx)
        # AND at least one of these supporting criteria
        with outer.any_of() as inner:
            inner.drug(cs_drug, within_days_before=30)
            inner.measurement(cs_lab, within_days_before=7)
            inner.procedure(cs_proc, within_days_after=14)
```

#### Using exclude inside groups

```python
with ev.rule("No Contraindications", weight=-5) as rule:
    with rule.all_of() as group:
        group.exclude_condition(cs_contraindication_a, anytime_before=True)
        group.exclude_condition(cs_contraindication_b, anytime_before=True)
```

## Common Patterns

### Incident Case Validation
Require a "clean" window before the event.

```python
# Pattern: Diagnosis present + no prior history
with ev.rule("Incident Diagnosis", weight=5) as rule:
    rule.condition(cs_dx).at_least(1)
    rule.exclude_condition(cs_dx, within_days_before=365)
```

### Lab Result Confirmation
Validate a code with a specific measurement value.

```python
ev.add_rule("Elevated LDL", weight=5).measurement(3027484).with_value(gt=130)
```

### Exclusion with Negative Weight
Use negative weights to penalize the phenotype score when contra-indicators are present.

```python
# The negative weight means this REDUCES the total score
with ev.rule("Prior Cancer History", weight=-10) as rule:
    rule.exclude_condition(cs_cancer, anytime_before=True)
```

### Multiple Exclusion Criteria

```python
with ev.rule("No Metastatic Disease", weight=-8) as rule:
    rule.exclude_condition(cs_metastasis_a, anytime_before=True)
    rule.exclude_condition(cs_metastasis_b, anytime_before=True)
    rule.exclude_condition(cs_metastasis_c, within_days_before=365)
```

### Complex Multi-domain Rule

```python
with ev.rule("Confirmed T2DM", weight=15) as rule:
    with rule.all_of() as must_have:
        must_have.condition(cs_t2dm)
        with must_have.any_of() as supporting:
            supporting.drug(cs_metformin, within_days_before=180)
            supporting.measurement(cs_hba1c, within_days_before=90)
            supporting.measurement(cs_fasting_glucose, within_days_before=90)
```

## Common Mistakes to Avoid

### ❌ Chaining `.at_least()` inside a group builder

```python
# WRONG — CriteriaGroupBuilder does not support .at_least() as a chained modifier
with rule.any_of() as group:
    group.condition(cs_id).at_least(2)  # AttributeError!
```

```python
# CORRECT — pass occurrence count as a keyword argument
with rule.any_of() as group:
    group.condition(cs_id, at_least=2)
```

### ❌ Using `at_most(0)` instead of `exclude_*`

```python
# Verbose way
rule.condition(cs_id).at_most(0).within_days_before(365)

# Preferred shorthand
rule.exclude_condition(cs_id, within_days_before=365)
```
