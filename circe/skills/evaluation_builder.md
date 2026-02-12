---
description: Build phenotype evaluation rubrics using the Pythonic EvaluationBuilder API
---

# Evaluation Builder Skill

Build phenotype evaluation rubrics (collections of weighted rules) using the `EvaluationBuilder` context manager.

## Key Principles

1.  **Use named rules** - Each rule should have a clear, human-readable name reflecting its clinical meaning.
2.  **Weighted Evidence** - Assign weights to rules based on their importance in the phenotype definition.
3.  **Positive vs Negative Evidence** - Use `polarity=1` for evidence of the phenotype and `polarity=-1` for evidence against it (exclusions).
4.  **Complex Logic** - Use nested logical groups (`any_of`, `all_of`) for sophisticated rules that require multiple criteria.

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
| `score` | `FLOAT` | The calculated score (`weight * polarity`) or `0` if not matched |

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
        
        # 2. Simple Rule
        ev.add_rule("GI Bleed Diagnosis", weight=10).condition(bleed).at_least(1)
        
        # 3. Complex Rule with Temporal Window
        with ev.rule("Recent Aspirin Use", weight=5) as rule:
            rule.drug(aspirin).at_least(1).within_days_before(30)
            
        # 4. Exclusion Rule (Negative Polarity)
        ev.add_rule("Alternative Diagnosis", weight=5, polarity=-1).condition(4329041)
        
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
ev.add_rule(name, weight, polarity=1, category=None)
```

-   `weight`: The numeric score assigned if the rule is matched.
-   `polarity`: `1` (positive evidence), `-1` (negative evidence/exclusion).
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
```

### Criteria Modifiers

```python
# Occurrence count
rule.at_least(N)

# Temporal windows (relative to index date)
rule.within_days_before(N)      # N days before index
rule.within_days_after(N)       # N days after index
rule.within_days(N)             # N days before AND after index (symmetric window)
rule.anytime_before()           # Any time before index
rule.anytime_after()            # Any time after index

# Value ranges (Measurements)
rule.measurement(id).with_value(gt=130)
rule.measurement(id).with_value(between=(6.0, 6.4))
```

### Logical Grouping (Nested Contexts)

For rules requiring multiple criteria:

```python
with ev.rule("Complex Evidence", weight=10) as rule:
    with rule.any_of() as any_group:
        any_group.condition(1)
        any_group.drug(2)
```

## Common Patterns

### Incident Case Validation
Require a "clean" window before the event.

```python
with ev.rule("Incident Diagnosis", weight=5) as rule:
    rule.condition(id).at_least(1)
    rule.exclude_condition(id).within_days_before(365)
```

### Lab Result Confirmation
Validate a code with a specific measurement value.

```python
ev.add_rule("Elevated LDL", weight=5).measurement(3027484).with_value(gt=130)
```
