"""
Basic Cohort Definition Example - Fluent Builder API

This example demonstrates how to create a simple cohort definition
for patients with Type 2 Diabetes using the fluent cohort builder API.
"""

from circe.cohort_builder import CohortBuilder
from circe.vocabulary import concept_set, descendants
from circe.api import build_cohort_query
from circe.cohortdefinition.cohort_expression_query_builder import BuildExpressionQueryOptions


def create_diabetes_cohort():
    """Create a simple Type 2 Diabetes cohort definition using the fluent API."""
    
    # Define the Type 2 Diabetes concept set using vocabulary helpers
    diabetes_concept_set = concept_set(
        descendants(201826),  # Type 2 diabetes mellitus
        id=1,
        name="Type 2 Diabetes Mellitus"
    )
    
    # Build cohort using fluent API
    cohort = (
        CohortBuilder("Patients with Type 2 Diabetes")
        .with_concept_sets(diabetes_concept_set)
        .with_condition(concept_set_id=1)  # Entry on T2DM diagnosis
        .first_occurrence()                 # First diagnosis only
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
    # Create the cohort definition
    print("Creating Type 2 Diabetes cohort definition (Fluent API)...")
    cohort = create_diabetes_cohort()
    
    # Display cohort information
    print(f"\nCohort Title: {cohort.title}")
    print(f"Number of Concept Sets: {len(cohort.concept_sets) if cohort.concept_sets else 0}")
    if cohort.concept_sets:
        print(f"Concept Set: {cohort.concept_sets[0].name}")
    
    # Generate SQL
    print("\nGenerating SQL...")
    sql = generate_sql_from_cohort(cohort)
    
    # Display first 500 characters of SQL
    print(f"\nGenerated SQL (first 500 chars):")
    print(sql[:500])
    print("...")
    
    # Save outputs
    output_file = "diabetes_cohort_fluent.sql"
    with open(output_file, "w") as f:
        f.write(sql)
    print(f"\nFull SQL saved to: {output_file}")
    
    json_output = cohort.model_dump_json(indent=2, by_alias=True, exclude_none=True)
    json_file = "diabetes_cohort_fluent.json"
    with open(json_file, "w") as f:
        f.write(json_output)
    print(f"Cohort definition saved to: {json_file}")
