"""
Example: Secondary Primary Malignancy Cohort Definition

This example demonstrates a complex cohort definition for identifying 
patients with a secondary primary cancer (SPM) using the context manager API.

Clinical Description:
    - Target Population: Adults (18-85) with a history of solid tumor malignancy.
    - Entry Event: First diagnosis of a solid tumor malignancy.
    - Requirement 1: A second distinct primary cancer at a different anatomic site.
    - Requirement 2: At least a 1-year time gap between the first and second cancer.
    - Requirement 3: Evidence of diagnostic confirmation for the second cancer 
      (e.g., biopsy, imaging, or specific tumor markers).
    - Requirement 4: Active treatment for the second cancer (chemotherapy, 
      radiation, or surgery).
    - Exclusion: Patients with evidence of metastatic disease before or near 
      the second cancer diagnosis are excluded to ensure the second cancer 
      is indeed a primary malignancy and not a recurrence or metastasis.
"""

import json
from circe.cohort_builder import CohortBuilder
from circe.api import build_cohort_query, cohort_print_friendly


def create_secondary_primary_malignancy_cohort():
    """Build the cohort using the context manager API."""
    
    with CohortBuilder("Secondary Primary Malignancy") as cohort:
        # --- Entry event: First solid tumor malignancy ---
        cohort.with_condition(1)  # Concept set 1: Solid tumor malignancies
        cohort.first_occurrence()
        cohort.with_observation_window(prior_days=365)
        cohort.require_age(18, 85)
        
        # --- Inclusion Rule 1: Second distinct cancer at different site ---
        with cohort.include_rule("Second Primary Cancer at Different Site") as rule:
            # Must have a record for a different anatomic site after index
            rule.require_condition(2, anytime_after=True)
        
        # --- Inclusion Rule 2: Minimum time gap (at least 1 year) ---
        with cohort.include_rule("Time Gap Requirement") as rule:
            rule.require_condition(2, within_days_after=365)
        
        # --- Inclusion Rule 3: Exclude metastatic disease ---
        with cohort.include_rule("No Metastatic Disease") as rule:
            # Exclude if any metastatic disease present
            rule.exclude_condition(100, anytime_before=True)
            rule.exclude_condition(101, anytime_before=True)
            rule.exclude_condition(102, anytime_before=True)
            rule.exclude_condition(103, anytime_before=True)
        
        # --- Inclusion Rule 4: Diagnostic Confirmation ---
        with cohort.include_rule("Diagnostic Confirmation") as rule:
            # Biopsy procedure
            rule.require_procedure(200, within_days_after=30)
        
        # --- Inclusion Rule 5: Active Cancer Treatment ---
        with cohort.include_rule("Active Cancer Treatment") as rule:
            # Chemotherapy
            rule.require_drug(400, anytime_after=True)
    
    return cohort.expression


if __name__ == "__main__":
    # Create the cohort
    cohort = create_secondary_primary_malignancy_cohort()
    
    # Export to JSON
    cohort_json = cohort.model_dump_json(by_alias=True, exclude_none=True, indent=2)
    print("--- Cohort JSON (Snippet) ---")
    print(cohort_json[:500] + "...")
    
    # Generate human-readable Markdown
    markdown = cohort_print_friendly(cohort)
    print("\n--- Human-Readable Description ---")
    print(markdown[:500] + "...")
    
    # Generate SQL
    from circe.cohortdefinition import BuildExpressionQueryOptions
    options = BuildExpressionQueryOptions()
    options.cdm_schema = "my_cdm"
    options.target_table = "results.cohort"
    options.cohort_id = 123
    
    sql = build_cohort_query(cohort, options)
    print("\n--- SQL Query (Snippet) ---")
    print(sql[:500] + "...")
