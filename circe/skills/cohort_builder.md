---
description: Build OHDSI cohort definitions using the Pythonic context manager API
---

# Cohort Builder Skill

Build OHDSI cohort definitions using the `CohortBuilder` context manager.

## Key Principles

1. **Use named concept sets** - Always attach concept sets to the cohort so they appear in output
2. **Return expressions from functions** - Define cohorts as functions for readability
3. **Save to cohorts directory** - Output multiple cohorts to a common directory by name
4. **Apply constraints only when clinically specified** - Do not add population filters (age, gender, observation windows) unless they are explicitly requested in the clinical description or essential to the phenotype definition. When in doubt, start broad and let the clinical description guide you.

## Basic Pattern

```python
from circe.cohort_builder import CohortBuilder
from circe.vocabulary import concept_set, descendants


def create_diabetes_cohort():
    """Create a Type 2 Diabetes cohort."""
    # Define concept sets (attached to cohort)
    t2dm = concept_set(descendants(201826), id=1, name="Type 2 Diabetes")
    metformin = concept_set(descendants(1503297), id=2, name="Metformin")
    
    with CohortBuilder("T2DM with Prior Metformin") as cohort:
        cohort.with_concept_sets(t2dm, metformin)
        cohort.with_condition(concept_set_id=1)
        cohort.first_occurrence()
        
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
# Occurrence limiting
cohort.first_occurrence()
cohort.all_occurrences()

# Observation period requirements (apply only if clinically necessary)
cohort.with_observation_window(prior_days=365, post_days=0)  # Example values

# Age constraints (apply only if specified in clinical description)
cohort.min_age(18)  # Example: minimum age
cohort.max_age(65)  # Example: maximum age
cohort.require_age(min_age=18, max_age=65)  # Example: age range

# Demographic constraints (apply only if specified in clinical description)
cohort.require_gender(8507, 8532)  # Example: gender concept IDs (separate args)
cohort.require_race(8527)  # Example: race concept ID
cohort.require_ethnicity(38003563)  # Example: ethnicity concept ID
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

## Decision Guide: When to Apply Population Constraints

Use this guide to determine whether to apply age, gender, observation window, or other population filters:

### ✅ Apply Age Constraints When:
- The clinical description explicitly mentions age (e.g., "adults 18+", "elderly 65+", "children under 12")
- The phenotype is inherently age-specific (e.g., "pediatric asthma", "geriatric hip fracture")
- Age is part of a validated algorithm (e.g., Sentinel, OMOP phenotype library)

### ❌ Do NOT Apply Age Constraints When:
- The clinical description does not mention age
- You're building a general population cohort
- The concept set itself defines the population (e.g., "pregnancy" is inherently age-restricted)

### ✅ Apply Observation Window When:
- You need to confirm "new" or "incident" cases (require prior observation to rule out prevalent cases)
- The phenotype requires baseline characteristics (need lookback period)
- The clinical description specifies continuous enrollment

### ❌ Do NOT Apply Observation Window When:
- Building a simple prevalence cohort
- The clinical description doesn't mention enrollment or baseline periods
- You're identifying all occurrences regardless of observation history

### ✅ Apply Gender/Race/Ethnicity When:
- The clinical description explicitly specifies demographic restrictions
- The phenotype is inherently demographic-specific (e.g., "prostate cancer" is male-specific)

### ❌ Do NOT Apply Demographic Filters When:
- The clinical description does not mention demographics
- You're building a general population cohort

### General Rule:
**When in doubt, start broad.** It's easier to add constraints later than to realize you've been excluding valid patients all along.


## Complete Example with Multiple Cohorts

```python
from pathlib import Path
from circe.cohort_builder import CohortBuilder
from circe.vocabulary import concept_set, descendants


def create_pediatric_asthma_cohort():
    """Pediatric asthma cohort - no age restriction applied.
    
    Note: No age filter is specified because the clinical definition
    does not restrict by age. The concept set itself defines the population.
    """
    asthma = concept_set(descendants(317009), id=1, name="Asthma")
    
    with CohortBuilder("Pediatric Asthma") as cohort:
        cohort.with_concept_sets(asthma)
        cohort.with_condition(concept_set_id=1)
        cohort.first_occurrence()
        # No age filter - let the data define the population
    
    return cohort.expression


def create_elderly_hip_fracture_cohort():
    """Hip fracture in elderly patients.
    
    Note: Age restriction IS applied here because it's clinically relevant
    to the phenotype definition (elderly-specific outcome).
    """
    hip_fx = concept_set(descendants(4230399), id=1, name="Hip Fracture")
    
    with CohortBuilder("Elderly Hip Fracture") as cohort:
        cohort.with_concept_sets(hip_fx)
        cohort.with_condition(concept_set_id=1)
        cohort.first_occurrence()
        cohort.min_age(65)  # Example: Age IS a clinical requirement here
    
    return cohort.expression


def create_new_diabetes_users_cohort():
    """New diabetes diagnosis with continuous enrollment.
    
    Note: Observation window IS applied because we need to ensure
    patients are observable before diagnosis (to confirm 'new' diagnosis).
    """
    t2dm = concept_set(descendants(201826), id=1, name="Type 2 Diabetes")
    
    with CohortBuilder("New Type 2 Diabetes") as cohort:
        cohort.with_concept_sets(t2dm)
        cohort.with_condition(concept_set_id=1)
        cohort.first_occurrence()
        # Example: Observation window ensures we can confirm "new" diagnosis
        cohort.with_observation_window(prior_days=365)
    
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
        ("pediatric_asthma", create_pediatric_asthma_cohort()),
        ("elderly_hip_fracture", create_elderly_hip_fracture_cohort()),
        ("new_type_2_diabetes", create_new_diabetes_users_cohort()),
    ]
    
    for name, expr in cohorts:
        path = save_cohort(expr, name)
        print(f"Saved: {path}")
```

## Common Pitfalls to Avoid

### 1. **The "Adult Default" Trap**
❌ **Wrong**: Automatically adding `cohort.min_age(18)` to every cohort  
✅ **Right**: Only add age constraints when clinically specified

### 2. **The "365-Day Observation" Assumption**
❌ **Wrong**: Adding `cohort.with_observation_window(prior_days=365)` by default  
✅ **Right**: Only require observation windows when needed for "new" diagnosis or baseline assessment

### 3. **Copying Boilerplate Without Thinking**
❌ **Wrong**: Copying entire example code including all constraints  
✅ **Right**: Read the clinical description carefully and apply only relevant constraints

### 4. **Ignoring the Clinical Description**
❌ **Wrong**: Building what you think the cohort should be  
✅ **Right**: Building exactly what the clinical description specifies

### Example of Correct Approach:

**Clinical Description**: "Patients with Type 2 Diabetes"

```python
# ✅ CORRECT: No age or observation window (not specified)
def create_t2dm_cohort():
    t2dm = concept_set(descendants(201826), id=1, name="Type 2 Diabetes")
    
    with CohortBuilder("Type 2 Diabetes") as cohort:
        cohort.with_concept_sets(t2dm)
        cohort.with_condition(concept_set_id=1)
        cohort.first_occurrence()
    
    return cohort.expression
```

```python
# ❌ WRONG: Added constraints not in description
def create_t2dm_cohort():
    t2dm = concept_set(descendants(201826), id=1, name="Type 2 Diabetes")
    
    with CohortBuilder("Type 2 Diabetes") as cohort:
        cohort.with_concept_sets(t2dm)
        cohort.with_condition(concept_set_id=1)
        cohort.first_occurrence()
        cohort.min_age(18)  # ← NOT SPECIFIED
        cohort.with_observation_window(prior_days=365)  # ← NOT SPECIFIED
    
    return cohort.expression
```
