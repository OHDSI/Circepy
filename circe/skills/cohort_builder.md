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

```

## Modifying Existing Cohorts

If you have an existing cohort definition in your context (as a `CohortExpression` object or JSON), you can modify it instead of creating a new one from scratch.

### When to Modify vs Create New

**✅ Modify an existing cohort when:**
- You need to make small adjustments to an existing definition
- You want to add/remove specific criteria while preserving the rest
- You're iterating on a cohort based on feedback
- The existing cohort is close to what you need

**❌ Create a new cohort when:**
- The changes are substantial (different entry event, completely different logic)
- You need a variant for comparison (keep both versions)
- The clinical description is fundamentally different

### Loading Existing Cohorts

Use `CohortBuilder.from_expression()` to load an existing cohort for modification:

```python
from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition import CohortExpression

# Load from JSON
existing_json = """{ ... cohort definition ... }"""
existing = CohortExpression.model_validate_json(existing_json)

# Load into builder for modification
with CohortBuilder.from_expression(existing) as cohort:
    # Make modifications here
    cohort.require_drug(5, within_days_before=30)
    cohort.remove_inclusion_rule("Old Rule")

modified = cohort.expression
```

### Modification Operations

#### Adding New Criteria

Use the same API as building new cohorts:

```python
with CohortBuilder.from_expression(existing) as cohort:
    # Add new inclusion criteria
    cohort.require_measurement(4, within_days_after=90)
    
    # Add new exclusion criteria
    cohort.exclude_condition(6, anytime_before=True)
    
    # Add new concept sets
    from circe.vocabulary import concept_set, descendants
    hba1c = concept_set(descendants(3004410), id=4, name="HbA1c")
    cohort.with_concept_sets(hba1c)
```

#### Removing Inclusion Rules

Remove rules by their name:

```python
with CohortBuilder.from_expression(existing) as cohort:
    # Remove a specific rule
    cohort.remove_inclusion_rule("Prior Treatment")
    
    # Or clear all rules and start fresh
    cohort.clear_inclusion_rules()
```

#### Removing Censoring Criteria

Remove censoring criteria by type, concept set ID, or index:

```python
with CohortBuilder.from_expression(existing) as cohort:
    # Remove by type
    cohort.remove_censoring_criteria(criteria_type="Death")
    
    # Remove by concept set ID
    cohort.remove_censoring_criteria(concept_set_id=5)
    
    # Remove by index
    cohort.remove_censoring_criteria(index=0)
    
    # Or clear all censoring criteria
    cohort.clear_censoring_criteria()
```

#### Removing Entry Events

Remove entry events while ensuring at least one remains:

```python
with CohortBuilder.from_expression(existing) as cohort:
    # Remove by concept set ID
    cohort.remove_entry_event(concept_set_id=1)
    
    # Remove by type (removes first match)
    cohort.remove_entry_event(criteria_type="DrugExposure")
    
    # Remove by index
    cohort.remove_entry_event(index=0)
```

**Note**: You cannot remove the last entry event. At least one must remain.

#### Removing Concept Sets

Remove concept sets with or without cleaning up references:

```python
with CohortBuilder.from_expression(existing) as cohort:
    # Remove just the concept set (leaves references)
    cohort.remove_concept_set(concept_set_id=3)
    
    # Remove concept set AND all criteria that reference it
    cohort.remove_all_references(concept_set_id=3)
```

**Recommendation**: Use `remove_all_references()` to avoid orphaned criteria.

#### Clearing Demographic Criteria

Remove all demographic restrictions:

```python
with CohortBuilder.from_expression(existing) as cohort:
    # Clear age, gender, race, ethnicity restrictions
    cohort.clear_demographic_criteria()
```

### Practical Modification Examples

#### Example 1: Refining an Existing Cohort

```python
def refine_diabetes_cohort(existing_cohort: CohortExpression):
    """Refine diabetes cohort by removing age restriction and adding HbA1c requirement."""
    
    # Add new concept set for HbA1c
    hba1c = concept_set(descendants(3004410), id=4, name="HbA1c Measurement")
    
    with CohortBuilder.from_expression(existing_cohort, title="Refined Diabetes Cohort") as cohort:
        # Remove age restriction (if it exists)
        cohort.clear_demographic_criteria()
        
        # Add HbA1c measurement requirement
        cohort.with_concept_sets(hba1c)
        cohort.require_measurement(4, within_days_after=90)
    
    return cohort.expression
```

#### Example 2: Removing Outdated Criteria

```python
def remove_outdated_exclusions(existing_cohort: CohortExpression):
    """Remove outdated exclusion criteria from cohort."""
    
    with CohortBuilder.from_expression(existing_cohort) as cohort:
        # Remove specific exclusion rules
        cohort.remove_inclusion_rule("Cancer Exclusion")
        cohort.remove_inclusion_rule("Pregnancy Exclusion")
        
        # Remove death censoring
        cohort.remove_censoring_criteria(criteria_type="Death")
    
    return cohort.expression
```

#### Example 3: Simplifying a Complex Cohort

```python
def simplify_cohort(existing_cohort: CohortExpression):
    """Simplify cohort by removing all inclusion rules and keeping only entry event."""
    
    with CohortBuilder.from_expression(existing_cohort, title="Simplified Cohort") as cohort:
        # Clear all inclusion rules
        cohort.clear_inclusion_rules()
        
        # Clear all censoring criteria
        cohort.clear_censoring_criteria()
        
        # Clear demographic restrictions
        cohort.clear_demographic_criteria()
    
    return cohort.expression
```

#### Example 4: Adapting for Different Population

```python
def adapt_for_pediatric_population(adult_cohort: CohortExpression):
    """Adapt an adult cohort for pediatric population."""
    
    with CohortBuilder.from_expression(adult_cohort, title="Pediatric Version") as cohort:
        # Remove adult age restriction
        cohort.clear_demographic_criteria()
        
        # Add pediatric age restriction
        cohort.max_age(17)
        
        # Remove adult-specific criteria (example)
        try:
            cohort.remove_inclusion_rule("Pregnancy Screening")
        except KeyError:
            pass  # Rule doesn't exist, continue
    
    return cohort.expression
```

### Decision Guide: Modify or Create New?

Use this flowchart to decide:

1. **Is the entry event the same?**
   - No → Create new cohort
   - Yes → Continue

2. **Are you changing >50% of the criteria?**
   - Yes → Consider creating new cohort
   - No → Continue

3. **Do you need to keep both versions?**
   - Yes → Create new cohort (with different title)
   - No → Modify existing

4. **Are the changes additive (adding criteria)?**
   - Yes → Modify existing
   - Mostly removals → Modify existing

5. **Is this a one-time adjustment or a variant?**
   - One-time → Modify existing
   - Variant → Create new with different title

### Important Notes

**Preservation of Original**: Modifications create a copy. The original `CohortExpression` is never mutated.

```python
original = CohortExpression.model_validate_json(json_data)

with CohortBuilder.from_expression(original) as cohort:
    cohort.clear_inclusion_rules()

modified = cohort.expression

# original is unchanged
assert len(original.inclusion_rules) > 0  # Still has rules
assert len(modified.inclusion_rules) == 0  # Rules cleared
```

**Error Handling**: Removal methods raise errors for invalid operations:

```python
try:
    cohort.remove_inclusion_rule("Nonexistent Rule")
except KeyError:
    print("Rule not found")

try:
    cohort.remove_entry_event(concept_set_id=999)
except ValueError:
    print("Entry event not found or would leave zero entry events")
```

**State Reconstruction Limitations**: Complex cohorts with deeply nested logic or correlated criteria may not be fully reconstructed. The modification API works best with:
- Simple inclusion/exclusion rules
- Standard time windows
- Common criteria types

For highly complex cohorts, consider creating a new one from scratch.

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
