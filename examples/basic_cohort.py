"""
Basic Cohort Definition Example

This example demonstrates how to create a simple cohort definition
for patients with Type 2 Diabetes using the CIRCE Python API.
"""

from circe import CohortExpression
from circe.cohortdefinition import PrimaryCriteria, ConditionOccurrence
from circe.cohortdefinition.core import ObservationFilter, ResultLimit
from circe.vocabulary import ConceptSet, ConceptSetExpression, ConceptSetItem, Concept
from circe.api import build_cohort_query


def create_diabetes_cohort():
    """Create a simple Type 2 Diabetes cohort definition."""
    
    # Define the Type 2 Diabetes concept set
    diabetes_concept_set = ConceptSet(
        id=1,
        name="Type 2 Diabetes Mellitus",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(
                        concept_id=201826,
                        concept_name="Type 2 diabetes mellitus",
                        domain_id="Condition",
                        vocabulary_id="SNOMED",
                        concept_class_id="Clinical Finding",
                        standard_concept="S",
                        concept_code="44054006"
                    ),
                    include_descendants=True,  # Include all child concepts
                    is_excluded=False
                )
            ]
        )
    )
    
    # Create the primary criteria (first occurrence of condition)
    primary_criteria = PrimaryCriteria(
        criteria_list=[
            ConditionOccurrence(
                codeset_id=1,  # References the concept set above
                first=True,     # Only the first occurrence
                condition_type_exclude=False
            )
        ],
        observation_window=ObservationFilter(
            prior_days=0,   # Must have observation period starting on or before event
            post_days=0     # Must have observation period ending on or after event
        ),
        primary_limit=ResultLimit(type="All")  # Include all matching events
    )
    
    # Create the complete cohort expression
    cohort = CohortExpression(
        title="Patients with Type 2 Diabetes",
        concept_sets=[diabetes_concept_set],
        primary_criteria=primary_criteria
    )
    
    return cohort


def generate_sql_from_cohort(cohort):
    """Generate SQL from the cohort definition."""
    
    sql = build_cohort_query(
        cohort,
        cdm_schema="my_cdm_schema",
        vocab_schema="my_vocab_schema",
        cohort_id=1
    )
    
    return sql


if __name__ == "__main__":
    # Create the cohort definition
    print("Creating Type 2 Diabetes cohort definition...")
    cohort = create_diabetes_cohort()
    
    # Display cohort information
    print(f"\nCohort Title: {cohort.title}")
    print(f"Number of Concept Sets: {len(cohort.concept_sets)}")
    print(f"Concept Set: {cohort.concept_sets[0].name}")
    
    # Generate SQL
    print("\nGenerating SQL...")
    sql = generate_sql_from_cohort(cohort)
    
    # Display first 500 characters of SQL
    print(f"\nGenerated SQL (first 500 chars):")
    print(sql[:500])
    print("...")
    
    # Optionally save to file
    output_file = "diabetes_cohort.sql"
    with open(output_file, "w") as f:
        f.write(sql)
    print(f"\nFull SQL saved to: {output_file}")
    
    # Optionally export as JSON
    json_output = cohort.model_dump_json(indent=2, exclude_none=True)
    json_file = "diabetes_cohort.json"
    with open(json_file, "w") as f:
        f.write(json_output)
    print(f"Cohort definition saved to: {json_file}")
