library(reticulate)

# Step 0 — Run the Python bootstrapping script - this is required due to the way reticulate interacts with the python
# interpreter - pydantic goes to many levels of depth and crashes
source_python("examples/reticulate_boot.py")

# Step 1 — Import CIRCE modules
circe <- import("circe")
circe_cd <- import("circe.cohortdefinition")
circe_core <- import("circe.cohortdefinition.core")
circe_query <- import("circe.cohortdefinition.cohort_expression_query_builder")
circe_vocab <- import("circe.vocabulary")
circe_api <- import("circe.api")

# Step 2 — Build concept set for Type 2 Diabetes
diabetes_concept_set <- circe_vocab$ConceptSet(
  id = 1L,
  name = "Type 2 Diabetes Mellitus",
  expression = circe_vocab$ConceptSetExpression(
    items = list(
      circe_vocab$ConceptSetItem(
        concept = circe_vocab$Concept(
          concept_id = 201826L,
          concept_name = "Type 2 diabetes mellitus",
          domain_id = "Condition",
          vocabulary_id = "SNOMED",
          concept_class_id = "Clinical Finding",
          standard_concept = "S",
          concept_code = "44054006"
        ),
        include_descendants = TRUE,
        is_excluded = FALSE
      )
    )
  )
)

# Step 3 — Define primary criteria
primary_criteria <- circe_cd$PrimaryCriteria(
  criteria_list = list(
    circe_cd$ConditionOccurrence(
      codeset_id = 1L,
      first = TRUE,
      condition_type_exclude = FALSE
    )
  ),
  observation_window = circe_core$ObservationFilter(
    prior_days = 0L,
    post_days = 0L
  ),
  primary_limit = circe_core$ResultLimit(type = "All")
)

# Step 4 — Build CohortExpression
cohort <- circe$CohortExpression(
  title = "Patients with Type 2 Diabetes",
  concept_sets = list(diabetes_concept_set),
  primary_criteria = primary_criteria
)

# Step 5 — Generate SQL from cohort
options <- circe_query$BuildExpressionQueryOptions()
options$cohort_id <- 1L
options$generate_stats <- TRUE

sql <- circe_api$build_cohort_query(cohort, options)

# Step 6 — Output results
cat("\nCohort Title:", cohort$title, "\n")
cat("Number of Concept Sets:", length(cohort$concept_sets), "\n")
cat("Concept Set Name:", cohort$concept_sets[[1]]$name, "\n")
cat("\nGenerated SQL (first 300 chars):\n", substr(sql, 1, 300), "\n")

# Step 2.8 — Save SQL and JSON
writeLines(sql, "diabetes_cohort.sql")
writeLines(cohort$model_dump_json(indent = 2L, by_alias = TRUE, exclude_none = TRUE),
           "diabetes_cohort.json")

cat("\nFiles saved: diabetes_cohort.sql and diabetes_cohort.json\n")
