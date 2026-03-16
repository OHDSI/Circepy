from circe.api import cohort_print_friendly
from circe.cohort_builder import CohortBuilder

# Define inferred concept sets


cohort = (
    CohortBuilder("Fournier's Gangrene Cohort")
    .with_concept_sets({"id":1, "name":"Fournier's Gangrene"})
    .with_condition(1) # Entry event: Diagnosis of Fournier's Gangrene (Concept Set ID 1)
    .build()
)

# To view the generated CIRCE JSON, you can call:
cohort_print_friendly(cohort)