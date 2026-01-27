---
description: Build OHDSI cohort definitions using the Pythonic context manager API
---

# Cohort Builder Skill

Build OHDSI cohort definitions using the `CohortBuilder` context manager.

## Key Principles

1. **Use named concept sets** - Always attach concept sets to the cohort so they appear in output
2. **Return expressions from functions** - Define cohorts as functions for readability
3. **Save to cohorts directory** - Output multiple cohorts to a common directory by name

## Basic Pattern

```python
from circe.cohort_builder import CohortBuilder
from circe.vocabulary import concept_set, descendants


def create_diabetes_cohort():
    """Create a Type 2 Diabetes cohort."""
    # Define concept sets (attached to cohort)
    t2dm = concept_set(descendants(201826), id=1, name="Type 2 Diabetes")
    metformin = concept_set(descendants(1503297), id=2, name="Metformin")
    
    with CohortBuilder("New T2DM on Metformin") as cohort:
        cohort.with_concept_sets(t2dm, metformin)
        cohort.with_condition(concept_set_id=1)
        cohort.first_occurrence()
        cohort.with_observation_window(prior_days=365)
        cohort.min_age(18)
        
        with cohort.include_rule("Prior Metformin") as rule:
            rule.require_drug(2, anytime_before=True)
    
    return cohort.expression


# Save cohort to file
if __name__ == "__main__":
    from pathlib import Path
    
    cohort = create_diabetes_cohort()
    output_dir = Path("cohorts")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "new_t2dm_on_metformin.json"
    output_file.write_text(cohort.model_dump_json(by_alias=True, indent=2))
```

## API Reference

### Context Manager

```python
with CohortBuilder("Title") as cohort:
    # Define cohort inside block
    cohort.with_condition(1)

expression = cohort.expression  # Access after block exits
```

### Concept Sets (Required for Output)

Always define and attach concept sets:

```python
from circe.vocabulary import concept_set, descendants

# Create concept sets with meaningful names
t2dm = concept_set(descendants(201826), id=1, name="Type 2 Diabetes")
metformin = concept_set(descendants(1503297), id=2, name="Metformin")

with CohortBuilder("My Cohort") as cohort:
    cohort.with_concept_sets(t2dm, metformin)  # Attach to cohort
    cohort.with_condition(concept_set_id=1)    # Reference by ID
```

### Entry Events

```python
cohort.with_condition(concept_set_id)
cohort.with_drug(concept_set_id)
cohort.with_procedure(concept_set_id)
cohort.with_measurement(concept_set_id)
cohort.with_observation(concept_set_id)
cohort.with_visit(concept_set_id)
cohort.with_death()
```

### Entry Configuration

```python
cohort.first_occurrence()
cohort.with_observation_window(prior_days=365, post_days=0)
cohort.min_age(18)
cohort.max_age(65)
cohort.require_age(min_age=18, max_age=65)
cohort.require_gender(8507, 8532)  # Separate args, NOT list
```

### Inclusion/Exclusion with Time Windows

```python
cohort.require_condition(id, within_days_before=30)
cohort.require_drug(id, anytime_before=True)
cohort.exclude_condition(id, within_days_after=90)
cohort.exclude_drug(id, same_day=True)
```

**Time window options:**
- `within_days_before=N`
- `within_days_after=N`
- `anytime_before=True`
- `anytime_after=True`
- `same_day=True`
- `during_event=True`

### Named Inclusion Rules

For attrition tracking, use nested contexts:

```python
with cohort.include_rule("Prior Treatment") as rule:
    rule.require_drug(2, anytime_before=True)

with cohort.include_rule("No Contraindications") as rule:
    rule.exclude_condition(3, within_days_before=365)
```

## Complete Example with Multiple Cohorts

```python
from pathlib import Path
from circe.cohort_builder import CohortBuilder
from circe.vocabulary import concept_set, descendants


def create_t2dm_cohort():
    """Adults with new T2DM diagnosis."""
    t2dm = concept_set(descendants(201826), id=1, name="Type 2 Diabetes")
    
    with CohortBuilder("New Type 2 Diabetes") as cohort:
        cohort.with_concept_sets(t2dm)
        cohort.with_condition(concept_set_id=1)
        cohort.first_occurrence()
        cohort.with_observation_window(prior_days=365)
        cohort.min_age(18)
    
    return cohort.expression


def create_metformin_cohort():
    """New metformin users."""
    metformin = concept_set(descendants(1503297), id=1, name="Metformin")
    
    with CohortBuilder("New Metformin Users") as cohort:
        cohort.with_concept_sets(metformin)
        cohort.with_drug(concept_set_id=1)
        cohort.first_occurrence()
        cohort.with_observation_window(prior_days=365)
        cohort.min_age(18)
    
    return cohort.expression


def save_cohort(expression, name: str, output_dir: Path = Path("cohorts")):
    """Save cohort expression to JSON file."""
    output_dir.mkdir(exist_ok=True)
    filename = name.lower().replace(" ", "_") + ".json"
    output_path = output_dir / filename
    output_path.write_text(expression.model_dump_json(by_alias=True, indent=2))
    return output_path


if __name__ == "__main__":
    cohorts = [
        ("new_type_2_diabetes", create_t2dm_cohort()),
        ("new_metformin_users", create_metformin_cohort()),
    ]
    
    for name, expr in cohorts:
        path = save_cohort(expr, name)
        print(f"Saved: {path}")
```
