"""
Example usage of the prompt builder for cohort generation.

This demonstrates how to use the CohortPromptBuilder to create
complete prompts for different AI models.
"""

from scripts.prompt_builder import CohortPromptBuilder, ConceptSet, create_prompt


def example_basic_usage():
    """Basic example: Create a prompt for a simple cohort."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Define concept sets
    concept_sets = [
        ConceptSet(1, "Type 2 Diabetes Mellitus", "Standard OMOP codes for T2DM"),
        ConceptSet(2, "Metformin", "All metformin formulations"),
        ConceptSet(3, "Insulin", "All insulin products")
    ]
    
    # Create prompt for standard model
    builder = CohortPromptBuilder()
    prompt = builder.build_prompt(
        clinical_description=(
            "Adults aged 18-65 with a new diagnosis of Type 2 Diabetes who have "
            "a prior history of Metformin use but no prior history of Insulin."
        ),
        concept_sets=concept_sets,
        model_type="standard"
    )
    
    # Display first 500 chars
    print("\nGenerated prompt (first 500 chars):")
    print(prompt[:500])
    print("...\n")
    print(f"Total prompt length: {len(prompt)} characters")
    print(f"Estimated tokens: ~{len(prompt.split()) * 1.3:.0f}\n")


def example_all_model_types():
    """Example: Create prompts for all model types."""
    print("=" * 60)
    print("Example 2: All Model Types")
    print("=" * 60)
    
    concept_sets = [
        ConceptSet(1, "Hypertension"),
        ConceptSet(2, "ACE Inhibitors"),
        ConceptSet(3, "Beta Blockers")
    ]
    
    clinical_desc = (
        "Patients with newly diagnosed hypertension who are started on "
        "ACE inhibitors but have no history of beta blocker use."
    )
    
    builder = CohortPromptBuilder()
    
    for model_type in ["reasoning", "standard", "fast"]:
        prompt = builder.build_prompt(
            clinical_description=clinical_desc,
            concept_sets=concept_sets,
            model_type=model_type
        )
        
        print(f"\n{model_type.upper()} model prompt:")
        print(f"  Length: {len(prompt)} chars")
        print(f"  Tokens: ~{len(prompt.split()) * 1.3:.0f}")
        print(f"  Lines: {len(prompt.splitlines())}")


def example_convenience_function():
    """Example: Using the convenience function with dicts."""
    print("=" * 60)
    print("Example 3: Convenience Function")
    print("=" * 60)
    
    # Use simple dicts instead of ConceptSet objects
    prompt = create_prompt(
        clinical_description="Patients aged 18+ with diabetes and HbA1c > 7%",
        concept_sets=[
            {"id": 1, "name": "Type 2 Diabetes"},
            {"id": 2, "name": "HbA1c Measurement", "description": "Hemoglobin A1c lab tests"}
        ],
        model_type="fast",
        additional_notes="Focus on patients with poor glycemic control"
    )
    
    print(f"\nGenerated prompt length: {len(prompt)} characters")
    print("Last 500 chars:")
    print(prompt[-500:])


def example_save_prompt():
    """Example: Save prompt to file."""
    print("=" * 60)
    print("Example 4: Save Prompt to File")
    print("=" * 60)
    
    builder = CohortPromptBuilder()
    
    concept_sets = [
        ConceptSet(1, "COVID-19", "SARS-CoV-2 infection diagnosis"),
        ConceptSet(2, "Mechanical Ventilation"),
        ConceptSet(3, "ICU Stay")
    ]
    
    prompt = builder.build_prompt(
        clinical_description=(
            "Patients hospitalized with COVID-19 who required mechanical "
            "ventilation or ICU admission within 7 days of diagnosis."
        ),
        concept_sets=concept_sets,
        model_type="standard"
    )
    
    # Save to file
    output_path = "example_covid_cohort_prompt.txt"
    builder.save_prompt(prompt, output_path, model_type="standard")


def example_complex_cohort():
    """Example: Complex cohort with multiple criteria."""
    print("=" * 60)
    print("Example 5: Complex Cohort")
    print("=" * 60)
    
    concept_sets = [
        ConceptSet(1, "Acute Myocardial Infarction", "AMI diagnosis codes"),
        ConceptSet(2, "Aspirin", "Antiplatelet therapy"),
        ConceptSet(3, "Statin", "Lipid-lowering therapy"),
        ConceptSet(4, "Beta Blocker", "Beta-adrenergic blocking agents"),
        ConceptSet(5, "ACE Inhibitor", "ACE inhibitor therapy"),
        ConceptSet(6, "Troponin", "Cardiac troponin test"),
        ConceptSet(7, "Chronic Kidney Disease", "CKD stages 3-5"),
        ConceptSet(8, "End-Stage Renal Disease", "ESRD or dialysis")
    ]
    
    clinical_desc = """
    Patients aged 18+ with a first acute myocardial infarction (AMI) diagnosis who:
    
    Inclusion criteria:
    - Have elevated troponin within 24 hours of AMI
    - Are prescribed aspirin within 7 days after AMI
    - Are prescribed a statin within 30 days after AMI
    - Have at least 365 days of prior observation
    
    Exclusion criteria:
    - History of chronic kidney disease in the 180 days prior to AMI
    - History of end-stage renal disease at any time prior to AMI
    - Prior use of beta blockers or ACE inhibitors in the 90 days before AMI
    
    Focus on guideline-concordant care for post-MI patients without contraindications.
    """
    
    prompt = create_prompt(
        clinical_description=clinical_desc,
        concept_sets=[
            {"id": cs.id, "name": cs.name, "description": cs.description}
            for cs in concept_sets
        ],
        model_type="standard"
    )
    
    print(f"\nComplex cohort prompt generated")
    print(f"  Total concept sets: {len(concept_sets)}")
    print(f"  Prompt length: {len(prompt)} characters")
    print(f"  Estimated tokens: ~{len(prompt.split()) * 1.3:.0f}")


if __name__ == "__main__":
    # Run all examples
    example_basic_usage()
    print("\n")
    example_all_model_types()
    print("\n")
    example_convenience_function()
    print("\n")
    example_save_prompt()
    print("\n")
    example_complex_cohort()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
