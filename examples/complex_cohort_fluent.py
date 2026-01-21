"""
Complex Cohort Definition Example - Fluent Builder API

This example demonstrates advanced features using the fluent builder:
- Entry event with first occurrence
- Age restrictions  
- Observation window requirements
- Inclusion criteria with time windows
- Exclusion criteria
"""

from circe.cohort_builder import CohortBuilder
from circe.vocabulary import concept_set, descendants
from circe.api import build_cohort_query
from circe.cohortdefinition.cohort_expression_query_builder import BuildExpressionQueryOptions


def create_complex_cohort():
    """
    Create a cohort for patients with:
    1. Type 2 Diabetes diagnosis (entry event)
    2. Age 18+ at index
    3. 365 days prior observation
    4. Metformin prescription within 30 days after diagnosis
    5. No insulin exposure in the 180 days before diagnosis
    6. HbA1c measurement within 180 days after diagnosis
    """
    
    # Define concept sets
    t2dm = concept_set(
        descendants(201826),  # Type 2 diabetes mellitus
        id=1,
        name="Type 2 Diabetes Mellitus"
    )
    
    metformin = concept_set(
        descendants(1503297),  # Metformin
        id=2,
        name="Metformin"
    )
    
    insulin = concept_set(
        descendants(1511348),  # Insulin
        id=3,
        name="Insulin"
    )
    
    hba1c = concept_set(
        descendants(3004410),  # HbA1c measurement
        id=4,
        name="Hemoglobin A1c"
    )
    
    # Build cohort using fluent API
    cohort = (
        CohortBuilder("T2DM Patients on Metformin (Complex)")
        .with_concept_sets(t2dm, metformin, insulin, hba1c)
        
        # Entry: First T2DM diagnosis
        .with_condition(concept_set_id=1)
        .first_occurrence()
        .with_observation(prior_days=365)
        .min_age(18)
        
        # Inclusion: Must have metformin within 30 days after
        .require_drug(concept_set_id=2)
            .within_days_after(30)
        
        # Inclusion: Must have HbA1c within 180 days after
        .require_measurement(concept_set_id=4)
            .within_days_after(180)
        
        # Exclusion: No prior insulin
        .exclude_drug(concept_set_id=3)
            .within_days_before(180)
        
        .build()
    )
    
    return cohort


def generate_sql_from_cohort(cohort):
    """Generate SQL from the cohort definition."""
    
    options = BuildExpressionQueryOptions()
    options.cohort_id = 1
    options.generate_stats = True
    
    sql = build_cohort_query(cohort, options)
    return sql


if __name__ == "__main__":
    print("Creating complex T2DM cohort definition (Fluent API)...")
    cohort = create_complex_cohort()
    
    # Display cohort information
    print(f"\nCohort Title: {cohort.title}")
    print(f"Number of Concept Sets: {len(cohort.concept_sets) if cohort.concept_sets else 0}")
    print(f"Has Primary Criteria: {cohort.primary_criteria is not None}")
    print(f"Number of Inclusion Rules: {len(cohort.inclusion_rules) if cohort.inclusion_rules else 0}")
    
    if cohort.concept_sets:
        print("\nConcept Sets:")
        for cs in cohort.concept_sets:
            print(f"  - {cs.name} (ID: {cs.id})")
    
    # Generate SQL
    print("\nGenerating SQL...")
    sql = generate_sql_from_cohort(cohort)
    
    # Display first 1000 characters of SQL
    print(f"\nGenerated SQL (first 1000 chars):")
    print(sql[:1000])
    print("...")
    
    # Save outputs
    output_file = "complex_cohort_fluent.sql"
    with open(output_file, "w") as f:
        f.write(sql)
    print(f"\nFull SQL saved to: {output_file}")
    
    json_output = cohort.model_dump_json(indent=2, by_alias=True, exclude_none=True)
    json_file = "complex_cohort_fluent.json"
    with open(json_file, "w") as f:
        f.write(json_output)
    print(f"Cohort definition saved to: {json_file}")
