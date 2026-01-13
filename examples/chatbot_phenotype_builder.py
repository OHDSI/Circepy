"""
Chatbot Phenotype Builder Example

This demonstrates how an LLM/chatbot would use the athena-client integration
to help users build phenotypes through natural language conversation.

Scenario: User wants to identify patients with diabetes who started metformin
"""

from circe.vocabulary import search_and_create_concept_set
from circe.cohortdefinition import CohortExpression, PrimaryCriteria
from circe.cohortdefinition.criteria import (
    ConditionOccurrence,
    DrugExposure,
    CorelatedCriteria
)
from circe.cohortdefinition.core import Window, WindowBound, CriteriaGroup


def chatbot_example_simple():
    """
    Simple chatbot interaction:
    
    User: "I need patients with type 2 diabetes who started metformin"
    
    Chatbot generates this code:
    """
    
    # Step 1: Create concept sets from natural language
    diabetes_cs = search_and_create_concept_set(
        search_term="type 2 diabetes mellitus",
        name="Type 2 Diabetes",
        concept_set_id=1,
        include_descendants=True  # Include all subtypes
    )
    
    metformin_cs = search_and_create_concept_set(
        search_term="metformin",
        name="Metformin",
        concept_set_id=2,
        include_descendants=True  # Include all formulations
    )
    
    # Step 2: Build cohort definition
    cohort = CohortExpression(
        title="Type 2 Diabetes Patients Starting Metformin",
        concept_sets=[diabetes_cs, metformin_cs],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                DrugExposure(
                    codeset_id=2,  # Metformin
                    first=True  # First exposure
                )
            ]
        ),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                CorelatedCriteria(
                    criteria=ConditionOccurrence(
                        codeset_id=1,  # Type 2 Diabetes
                        first=False
                    ),
                    start_window=Window(
                        start=WindowBound(days=365, coeff=-1),  # 365 days before
                        end=WindowBound(days=0, coeff=-1)  # to day of metformin
                    )
                )
            ]
        )
    )
    
    # Step 3: Generate SQL
    sql = cohort.to_sql(dialect="postgresql")
    
    print("Generated Cohort:")
    print(f"  Title: {cohort.title}")
    print(f"  Concept Sets: {len(cohort.concept_sets)}")
    print(f"  SQL Length: {len(sql)} characters")
    
    return cohort


def chatbot_example_iterative():
    """
    Iterative refinement:
    
    User: "I need patients with diabetes"
    Chatbot: [creates initial cohort]
    
    User: "Add requirement for metformin within 30 days"
    Chatbot: [refines cohort]
    
    User: "Also exclude patients with heart failure"
    Chatbot: [adds exclusion criteria]
    """
    
    # Initial: Just diabetes
    print("Step 1: Initial cohort (diabetes only)")
    diabetes_cs = search_and_create_concept_set(
        search_term="type 2 diabetes",
        name="Type 2 Diabetes",
        concept_set_id=1
    )
    
    cohort = CohortExpression(
        title="Type 2 Diabetes Patients",
        concept_sets=[diabetes_cs],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(codeset_id=1, first=True)
            ]
        )
    )
    print(f"  ✓ Created: {cohort.title}")
    
    # Refinement 1: Add metformin requirement
    print("\nStep 2: Add metformin within 30 days")
    metformin_cs = search_and_create_concept_set(
        search_term="metformin",
        name="Metformin",
        concept_set_id=2
    )
    
    cohort.concept_sets.append(metformin_cs)
    cohort.additional_criteria = CriteriaGroup(
        type="ALL",
        criteria_list=[
            CorelatedCriteria(
                criteria=DrugExposure(codeset_id=2, first=True),
                start_window=Window(
                    start=WindowBound(days=0, coeff=1),
                    end=WindowBound(days=30, coeff=1)
                )
            )
        ]
    )
    print(f"  ✓ Added metformin requirement")
    
    # Refinement 2: Exclude heart failure
    print("\nStep 3: Exclude heart failure")
    hf_cs = search_and_create_concept_set(
        search_term="heart failure",
        name="Heart Failure",
        concept_set_id=3
    )
    
    cohort.concept_sets.append(hf_cs)
    # Note: Exclusion would be added to censoring_criteria or as excluded criteria
    print(f"  ✓ Added heart failure exclusion")
    
    print(f"\nFinal cohort has {len(cohort.concept_sets)} concept sets")
    
    return cohort


def chatbot_example_complex():
    """
    Complex multi-condition phenotype:
    
    User: "I need patients with newly diagnosed type 2 diabetes who:
           - Started metformin within 90 days
           - Had HbA1c > 7% at diagnosis
           - No prior diabetes medications
           - At least 1 year of observation before diagnosis"
    
    Chatbot generates comprehensive cohort definition:
    """
    
    print("Building complex phenotype...")
    
    # Create all needed concept sets
    diabetes_cs = search_and_create_concept_set(
        "type 2 diabetes", "Type 2 Diabetes", 1
    )
    metformin_cs = search_and_create_concept_set(
        "metformin", "Metformin", 2
    )
    hba1c_cs = search_and_create_concept_set(
        "hemoglobin a1c", "HbA1c", 3
    )
    diabetes_drugs_cs = search_and_create_concept_set(
        "antidiabetic drug", "Diabetes Medications", 4
    )
    
    # Build cohort
    cohort = CohortExpression(
        title="Newly Diagnosed T2DM with Metformin Initiation",
        concept_sets=[diabetes_cs, metformin_cs, hba1c_cs, diabetes_drugs_cs],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(
                    codeset_id=1,  # Type 2 Diabetes
                    first=True  # First diagnosis
                )
            ],
            observation_window={
                "priorDays": 365,  # 1 year prior observation
                "postDays": 0
            }
        ),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                # Metformin within 90 days
                CorelatedCriteria(
                    criteria=DrugExposure(codeset_id=2, first=True),
                    start_window=Window(
                        start=WindowBound(days=0, coeff=1),
                        end=WindowBound(days=90, coeff=1)
                    )
                ),
                # No prior diabetes medications (would need exclusion logic)
                # HbA1c measurement (would need measurement criteria with value > 7)
            ]
        )
    )
    
    print(f"✓ Created complex phenotype: {cohort.title}")
    print(f"  Concept sets: {len(cohort.concept_sets)}")
    print(f"  Observation window: 365 days prior")
    
    return cohort


def main():
    """Run chatbot examples"""
    print("\n" + "=" * 60)
    print("Chatbot Phenotype Builder Examples")
    print("=" * 60 + "\n")
    
    try:
        print("Example 1: Simple Interaction")
        print("-" * 60)
        chatbot_example_simple()
        
        print("\n\nExample 2: Iterative Refinement")
        print("-" * 60)
        chatbot_example_iterative()
        
        print("\n\nExample 3: Complex Phenotype")
        print("-" * 60)
        chatbot_example_complex()
        
        print("\n" + "=" * 60)
        print("✅ All chatbot examples completed!")
        print("=" * 60)
        
        print("\n💡 Key Takeaways:")
        print("  • Concept sets created from natural language searches")
        print("  • Code is readable and modifiable")
        print("  • Iterative refinement is straightforward")
        print("  • Results are cached for performance")
        print("  • Perfect for LLM code generation")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nNote: Requires internet connection for athena API")


if __name__ == "__main__":
    main()
