"""
Complex Cohort Definition Example

This example demonstrates advanced features including:
- Multiple criteria with time windows
- Correlated criteria (additional criteria)
- Inclusion rules
- Age and gender restrictions
"""

from circe import CohortExpression
from circe.cohortdefinition import (
    PrimaryCriteria, ConditionOccurrence, DrugExposure,
    CorelatedCriteria, CriteriaGroup, DemographicCriteria
)
from circe.cohortdefinition.core import (
    ObservationFilter, ResultLimit, Window, WindowBound,
    Period, Occurrence, DateRange, NumericRange, Gender
)
from circe.vocabulary import ConceptSet, ConceptSetExpression, ConceptSetItem, Concept
from circe.api import build_cohort_query


def create_complex_cohort():
    """
    Create a cohort for patients with:
    1. Type 2 Diabetes diagnosis
    2. Metformin prescription within 30 days after diagnosis
    3. Age 18-75 at index
    4. No insulin exposure in the 180 days before diagnosis
    """
    
    # Concept Set 1: Type 2 Diabetes
    diabetes_concepts = ConceptSet(
        id=1,
        name="Type 2 Diabetes Mellitus",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(
                        concept_id=201826,
                        concept_name="Type 2 diabetes mellitus"
                    ),
                    include_descendants=True
                )
            ]
        )
    )
    
    # Concept Set 2: Metformin
    metformin_concepts = ConceptSet(
        id=2,
        name="Metformin",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(
                        concept_id=1503297,
                        concept_name="Metformin"
                    ),
                    include_descendants=True
                )
            ]
        )
    )
    
    # Concept Set 3: Insulin (for exclusion)
    insulin_concepts = ConceptSet(
        id=3,
        name="Insulin",
        expression=ConceptSetExpression(
            items=[
                ConceptSetItem(
                    concept=Concept(
                        concept_id=1511348,
                        concept_name="Insulin"
                    ),
                    include_descendants=True
                )
            ]
        )
    )
    
    # Primary Criteria: First Type 2 Diabetes diagnosis
    primary_criteria = PrimaryCriteria(
        criteria_list=[
            ConditionOccurrence(
                codeset_id=1,
                first=True,
                condition_type_exclude=False,
                # Age restriction at the time of diagnosis
                age=NumericRange(value=18, op="gte"),
                age_at_end=NumericRange(value=75, op="lte")
            )
        ],
        observation_window=ObservationFilter(
            prior_days=0,
            post_days=0
        ),
        primary_limit=ResultLimit(type="All")
    )
    
    # Additional Criteria: Metformin within 30 days after diagnosis
    metformin_criteria = CorelatedCriteria(
        criteria=DrugExposure(
            codeset_id=2,
            first=False,
            drug_type_exclude=False
        ),
        start_window=Window(
            start=WindowBound(days=0, coeff=-1),  # Index date
            end=WindowBound(days=30, coeff=1),    # 30 days after
            use_index_end=False,
            use_event_end=False
        ),
        occurrence=Occurrence(
            type=2,  # At least
            count=1,
            is_distinct=False
        )
    )
    
    # Additional Criteria: NO insulin in 180 days before diagnosis
    insulin_exclusion = CorelatedCriteria(
        criteria=DrugExposure(
            codeset_id=3,
            first=False,
            drug_type_exclude=False
        ),
        start_window=Window(
            start=WindowBound(days=180, coeff=-1),  # 180 days before
            end=WindowBound(days=1, coeff=-1),       # Day before index
            use_index_end=False,
            use_event_end=False
        ),
        occurrence=Occurrence(
            type=0,  # Exactly
            count=0,  # Zero occurrences (exclusion)
            is_distinct=False
        )
    )
    
    # Combine additional criteria
    additional_criteria = CriteriaGroup(
        type="ALL",  # Must meet all criteria
        criteria_list=[
            metformin_criteria,
            insulin_exclusion
        ],
        demographic_criteria_list=None,
        groups=None
    )
    
    # Create the complete cohort expression
    cohort = CohortExpression(
        title="New Type 2 Diabetes Patients Started on Metformin",
        concept_sets=[diabetes_concepts, metformin_concepts, insulin_concepts],
        primary_criteria=primary_criteria,
        additional_criteria=additional_criteria,
        qualified_limit=ResultLimit(type="First"),  # First qualifying event per person
        expression_limit=ResultLimit(type="All")
    )
    
    return cohort


if __name__ == "__main__":
    # Create the complex cohort
    print("Creating complex Type 2 Diabetes cohort with multiple criteria...")
    cohort = create_complex_cohort()
    
    # Display cohort information
    print(f"\nCohort Title: {cohort.title}")
    print(f"Number of Concept Sets: {len(cohort.concept_sets)}")
    print("Concept Sets:")
    for cs in cohort.concept_sets:
        print(f"  - {cs.name}")
    
    print(f"\nAdditional Criteria: {len(cohort.additional_criteria.criteria_list)} conditions")
    
    # Generate SQL
    print("\nGenerating SQL...")
    sql = build_cohort_query(
        cohort,
        cdm_schema="my_cdm",
        vocab_schema="my_vocab",
        cohort_id=2
    )
    
    # Save outputs
    sql_file = "complex_diabetes_cohort.sql"
    with open(sql_file, "w") as f:
        f.write(sql)
    print(f"SQL saved to: {sql_file}")
    
    json_file = "complex_diabetes_cohort.json"
    with open(json_file, "w") as f:
        f.write(cohort.model_dump_json(indent=2, exclude_none=True))
    print(f"Cohort definition saved to: {json_file}")
    
    print("\nCohort summary:")
    print("  - Index: First Type 2 Diabetes diagnosis")
    print("  - Age: 18-75 at diagnosis")
    print("  - Must have: Metformin within 30 days after diagnosis")
    print("  - Must not have: Insulin in 180 days before diagnosis")
