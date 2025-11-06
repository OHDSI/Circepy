#!/usr/bin/env Rscript
# cohort_sql_generator.R - Generate cohort SQL from JSON definitions using OHDSI circeR
# Usage: R CMD BATCH "--args input.json output.sql" cohort_sql_generator.R
# or: Rscript cohort_sql_generator.R input.json output.sql

## DO NOT NOT MODIFY

# Load required packages
if (!require("CirceR", quietly = TRUE)) {
  stop("CirceR package is required but not installed. See: https://github.com/OHDSI/CirceR")
}

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)

# Check for correct number of arguments
if (length(args) < 2) {
  stop("Usage: Rscript cohort_sql_generator.R <input_json_file> <output_sql_file> [cohort_id]")
}

input_file <- args[1]
output_file <- args[2]
cohort_id <- if (length(args) > 2) as.integer(args[3]) else 1

# Validate input file exists
if (!file.exists(input_file)) {
  stop("Input file does not exist: ", input_file)
}

cat("Reading cohort definition from:", input_file, "\n")
cat("Writing SQL to:", output_file, "\n")
cat("Using cohort ID:", cohort_id, "\n")

tryCatch({
  # Read JSON cohort definition
  cohort_json <- readChar(input_file, file.info(input_file)$size)
  
  # Convert JSON to cohort expression object [citation:2][citation:3]
  cohort_expression <- CirceR::cohortExpressionFromJson(cohort_json)
  
  # Generate SQL from cohort expression [citation:1][citation:5]
  # Options can be customized as needed
  generate_options <- CirceR::createGenerateOptions(
    generateStats = TRUE  # Include inclusion rule statistics
  )
  
  cohort_sql <- CirceR::buildCohortQuery(
    expression = cohort_expression, 
    options = generate_options
  )
  
  # Write SQL to output file
  writeLines(cohort_sql, output_file)
  
  # Optional: Also generate human-readable markdown version
  markdown <- CirceR::cohortPrintFriendly(cohort_expression)
  markdown_file <- paste0(tools::file_path_sans_ext(output_file), ".md")
  writeLines(markdown, markdown_file)
  
  cat("Successfully generated cohort SQL\n")
  cat("SQL output:", output_file, "\n")
  cat("Markdown documentation:", markdown_file, "\n")
  
}, error = function(e) {
  stop("Error generating cohort SQL: ", e$message)
})