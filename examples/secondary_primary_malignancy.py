"""
Example: Secondary Primary Malignancy Cohort Definition

This example demonstrates a complex, nested cohort definition for identifying 
patients with a secondary primary malignancy (SPM). An SPM is a second 
distinct cancer occurring in a different anatomic site from the original cancer,
at least one year after the initial diagnosis, and which is not metastatic disease.

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
    # Build the cohort using the fluent CohortBuilder API
    builder = (
        CohortBuilder("Secondary Primary Malignancy")
        # --- Entry event: First solid tumor malignancy ---
        .with_condition(1)  # Concept set 1: Solid tumor malignancies
        .first_occurrence()
        .with_observation(prior_days=365)  # Require 1 year of prior observation
        .require_age(18, 85)
        
        # --- Inclusion Rule 1: Second distinct cancer at different site ---
        .begin_rule("Second Primary Cancer at Different Site")
        .all_of()  # ALL of the following must be true:
            # Must have a record for a different anatomic site
            .require_condition(2)\
                .anytime_in_future(years=10)\
                .at_least(1)
            
            # AND must have at least one of these specific cancer types
            .any_of()
                .require_condition(10).anytime_in_future(years=10)  # Breast
                .require_condition(11).anytime_in_future(years=10)  # Lung
                .require_condition(12).anytime_in_future(years=10)  # Colorectal
                .require_condition(13).anytime_in_future(years=10)  # Prostate
            .end_group()
        .end_group()
        
        # --- Inclusion Rule 2: Minimum time gap (at least 1 year) ---
        .begin_rule("Time Gap Requirement")
        .require_condition(2)\
            .with_distinct()\
            .within_days_after(365)  # Must be at least 365 days after first cancer
        
        # --- Inclusion Rule 3: Exclude metastatic disease ---
        .begin_rule("No Metastatic Disease")
        .exclude_any_of(
            condition_ids=[100, 101, 102, 103]  # Metastasis concept sets
        )
        
        # --- Inclusion Rule 4: Diagnostic Confirmation ---
        .begin_rule("Diagnostic Confirmation")
        .at_least_of(1)  # At least one of these must be found:
            # 1. Pathology procedure (biopsy)
            .require_procedure(200)\
                .with_modifier(4184637)\
                .within_days_after(0)
            
            # 2. Imaging studies
            .require_procedure(201)\
                .with_quantity(min_qty=1)\
                .within_days_after(0)
            
            # 3. Specific tumor markers
            .require_measurement(300)\
                .with_operator(4172704)\
                .with_distinct()\
                .at_least(2)\
                .anytime_in_future(years=1)
        .end_group()
        
        # --- Inclusion Rule 5: Active Cancer Treatment ---
        .begin_rule("Active Cancer Treatment")
        .any_of()
            # 1. Chemotherapy (Intravenous)
            .require_drug(400)\
                .with_route(4112421)\
                .anytime_in_future(years=2)
            
            # 2. Radiation (Same visit)
            .require_procedure(500)\
                .between_visits()\
                .anytime_in_future(years=2)
            
            # 3. Surgery (Excision)
            .require_procedure(600)\
                .with_modifier(4301351)\
                .anytime_in_future(years=2)
        .end_group()
    )
    
    # Finalize the cohort
    cohort_expression = builder.build()
    return cohort_expression

if __name__ == "__main__":
    # 1. Create the cohort
    cohort = create_secondary_primary_malignancy_cohort()
    
    # 2. Export to JSON (for use in ATLAS or other tools)
    cohort_json = cohort.model_dump_json(by_alias=True, exclude_none=True, indent=2)
    print("--- Cohort JSON (Snippet) ---")
    print(cohort_json[:500] + "...")
    
    # 3. Generate human-readable Markdown (Print Friendly)
    markdown = cohort_print_friendly(cohort)
    print("\n--- Human-Readable Description ---")
    print(markdown[:500] + "...")
    
    # 4. Generate SQL for BigQuery (or other dialect)
    from circe.cohortdefinition import BuildExpressionQueryOptions
    options = BuildExpressionQueryOptions()
    options.cdm_schema = "my_cdm"
    options.target_table = "results.cohort"
    options.cohort_id = 123
    
    sql = build_cohort_query(cohort, options)
    print("\n--- SQL Query (Snippet) ---")
    print(sql[:500] + "...")
