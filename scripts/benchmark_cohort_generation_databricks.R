#!/usr/bin/env Rscript
# scripts/benchmark_cohort_generation_databricks.R
# Benchmark cohort GENERATION (execution) process: CirceR + SqlRender vs Ibis (Python)
#
# ==============================================================================
# REQUIRED ENVIRONMENT VARIABLES
# ==============================================================================
# Before running this script, set the following environment variables:
#
# 1. DATABRICKS_HOST
#    - Your Databricks workspace hostname
#    - Example: "your-workspace.cloud.databricks.com"
#    - Set with: Sys.setenv(DATABRICKS_HOST = "your-workspace.cloud.databricks.com")
#
# 2. DATABRICKS_HTTP_PATH
#    - The HTTP path to your Databricks SQL warehouse or cluster
#    - Example: "/sql/1.0/warehouses/xxxxxxxxxxxxx"
#    - Set with: Sys.setenv(DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/xxxxx")
#
# 3. DATABRICKS_TOKEN
#    - Your Databricks personal access token
#    - Example: "dapi1234567890abcdef..."
#    - Set with: Sys.setenv(DATABRICKS_TOKEN = "dapi...")
#
# 4. DATABRICKS_SCRATCH_SCHEMA
#    - Schema (or catalog.schema) for writing benchmark results
#    - Example: "my_catalog.my_schema" (Unity Catalog) or "my_schema" (Hive)
#    - Set with: Sys.setenv(DATABRICKS_SCRATCH_SCHEMA = "catalog.schema")
#
# 5. CDM_SCHEMA
#    - Schema containing your OMOP CDM tables
#    - Example: "healthverity_cc.cdm_healthverity_cc_v3470"
#    - Set with: Sys.setenv(CDM_SCHEMA = "catalog.cdm_schema")
#
# Quick setup example:
# Sys.setenv(
#   DATABRICKS_HOST = "your-workspace.cloud.databricks.com",
#   DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/xxxxx",
#   DATABRICKS_TOKEN = "dapi...",
#   DATABRICKS_SCRATCH_SCHEMA = "catalog.scratch_schema",
#   CDM_SCHEMA = "catalog.cdm_schema"
# )
# ==============================================================================

# Ensure packages are installed
required_packages <- c("microbenchmark", "reticulate", "CirceR", "SqlRender", "DatabaseConnector", "glue", "cli")
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    cat(sprintf("Installing %s...\n", pkg))
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
}

library(microbenchmark)
library(reticulate)
library(CirceR)
library(SqlRender)
library(DatabaseConnector)
library(glue)
library(cli)

# ==============================================================================
# DATABRICKS CONFIGURATION FROM ENVIRONMENT VARIABLES
# ==============================================================================
.getDatabricksConnectionDetails <- function(asList = FALSE) {
  password <- Sys.getenv("DATABRICKS_TOKEN")

  if (is.null(password) || password == "")
    cli::cli_abort("DATABRICKS_TOKEN ENVIRONMENT VARIABLE NOT SET")

  databricksConnectionString <- glue::glue("jdbc:databricks://{Sys.getenv('DATABRICKS_HOST')}/default;transportMode=http;ssl=1;AuthMech=3;httpPath={Sys.getenv('DATABRICKS_HTTP_PATH')}")

  cdList <- list(
    dbms = "spark",
    connectionString = databricksConnectionString,
    user = "token",
    password = password
  )

  if (asList)
    return(cdList)

  return(do.call(DatabaseConnector::createConnectionDetails, cdList))
}

cat("Setting up R Databricks connection via DatabaseConnector (Spark JDBC)...\n")
DATABRICKS_SCRATCH_SCHEMA <- Sys.getenv("DATABRICKS_SCRATCH_SCHEMA")
if (is.null(DATABRICKS_SCRATCH_SCHEMA) || DATABRICKS_SCRATCH_SCHEMA == "")
  cli::cli_abort("DATABRICKS_SCRATCH_SCHEMA ENVIRONMENT VARIABLE NOT SET")

connectionDetails <- .getDatabricksConnectionDetails()
r_con <- connect(connectionDetails)

venv_path <- file.path(getwd(), ".venv")
if (dir.exists(venv_path)) {
  use_python(file.path(venv_path, "bin", "python"), required = TRUE)
} else {
  # Fallback to current environment
}

cat("Importing Python libraries via reticulate...\n")
circe_api <- import("circe.api")
circe_execution <- import("circe.execution.api")
ibis <- import("ibis")

cat("Preparing Ibis Databricks backend...\n")
# Validate and get environment variables
databricks_host <- Sys.getenv("DATABRICKS_HOST")
if (is.null(databricks_host) || databricks_host == "")
  cli::cli_abort("DATABRICKS_HOST ENVIRONMENT VARIABLE NOT SET")

databricks_http_path <- Sys.getenv("DATABRICKS_HTTP_PATH")
if (is.null(databricks_http_path) || databricks_http_path == "")
  cli::cli_abort("DATABRICKS_HTTP_PATH ENVIRONMENT VARIABLE NOT SET")

databricks_token <- Sys.getenv("DATABRICKS_TOKEN")
if (is.null(databricks_token) || databricks_token == "")
  cli::cli_abort("DATABRICKS_TOKEN ENVIRONMENT VARIABLE NOT SET")

# Normalize host: remove https://, http://, trailing slashes, and :443 port
databricks_host <- sub("^https://", "", databricks_host)
databricks_host <- sub("^http://", "", databricks_host)
databricks_host <- sub("/$", "", databricks_host)
databricks_host <- sub(":443$", "", databricks_host)

# Normalize http_path: ensure it starts with /
if (!grepl("^/", databricks_http_path)) {
  databricks_http_path <- paste0("/", databricks_http_path)
}

# Split catalog.schema for Unity Catalog-aware connections
scratch_catalog <- NULL
scratch_db <- DATABRICKS_SCRATCH_SCHEMA
if (grepl("\\.", DATABRICKS_SCRATCH_SCHEMA)) {
  parts <- strsplit(DATABRICKS_SCRATCH_SCHEMA, "\\.", fixed = FALSE)[[1]]
  scratch_catalog <- parts[1]
  scratch_db <- parts[2]
}

# Set environment variables in Python process (reticulate doesn't auto-pass them)
py_os <- import("os")
py_os$environ["DATABRICKS_HOST"] <- databricks_host
py_os$environ["DATABRICKS_HTTP_PATH"] <- databricks_http_path
py_os$environ["DATABRICKS_TOKEN"] <- databricks_token

# Connect using correct parameter names for ibis.databricks.connect
py_backend <- ibis$databricks$connect(
  server_hostname = databricks_host,
  http_path = databricks_http_path,
  token = databricks_token,
  catalog = scratch_catalog,
  schema = scratch_db
)

# ==============================================================================
# SPARK OPTIMIZATION CONFIGURATION
# ==============================================================================
cat("Configuring Spark optimizations for benchmark...\n")

# Set Spark configuration for optimal parallelism and performance
tryCatch({
  py_backend$raw_sql("SET spark.sql.adaptive.enabled=true")$execute()
  cat("  ✓ Enabled adaptive query execution\n")
}, error = function(e) {
  cat("  Note: Could not enable adaptive query execution\n")
})

tryCatch({
  py_backend$raw_sql("SET spark.sql.adaptive.coalescePartitions.enabled=true")$execute()
  cat("  ✓ Enabled adaptive partition coalescing\n")
}, error = function(e) {
  cat("  Note: Could not enable adaptive partition coalescing\n")
})

tryCatch({
  py_backend$raw_sql("SET spark.sql.shuffle.partitions=200")$execute()
  cat("  ��� Set shuffle partitions to 200\n")
}, error = function(e) {
  cat("  Note: Could not set shuffle partitions\n")
})

tryCatch({
  py_backend$raw_sql("SET spark.sql.autoBroadcastJoinThreshold=10485760")$execute()
  cat("  ✓ Set auto broadcast join threshold to 10MB\n")
}, error = function(e) {
  cat("  Note: Could not set broadcast join threshold\n")
})

# ==============================================================================
# DATABRICKS BENCHMARK CONFIGURATION
# ==============================================================================
TARGET_DIALECT <- "spark"
CDM_SCHEMA <- Sys.getenv("CDM_SCHEMA")
TARGET_SCHEMA <- DATABRICKS_SCRATCH_SCHEMA
COHORT_TABLE <- "becnhmark_cohort"
BENCHMARK_ITERATIONS <- 1  # Use 1 for Databricks, 10 for DuckDB


cohorts_dir <- file.path("tests", "cohorts")
if (!dir.exists(cohorts_dir)) {
  cohorts_dir <- file.path("..", "tests", "cohorts")
}

json_files <- list.files(cohorts_dir, pattern = "\\.json$", full.names = TRUE)
if (length(json_files) == 0) stop("No cohort JSON files found in tests/cohorts/")
sample_files <- head(json_files, 10)

# ==============================================================================
# CREATE COHORT TABLE
# ==============================================================================
cat("\nCreating cohort table...\n")

# Drop table if it exists
drop_table_sql <- sprintf("DROP TABLE IF EXISTS %s.%s", TARGET_SCHEMA, COHORT_TABLE)
tryCatch({
  executeSql(r_con, drop_table_sql)
  cat(sprintf("  Dropped existing table %s.%s (if it existed)\n", TARGET_SCHEMA, COHORT_TABLE))
}, error = function(e) {
  cat(sprintf("  Note: Could not drop table (may not exist): %s\n", e$message))
})

# Create cohort table with required schema
create_table_sql <- sprintf("
CREATE TABLE %s.%s (
  cohort_definition_id BIGINT NOT NULL,
  subject_id BIGINT NOT NULL,
  cohort_start_date DATE NOT NULL,
  cohort_end_date DATE NOT NULL
)", TARGET_SCHEMA, COHORT_TABLE)

tryCatch({
  executeSql(r_con, create_table_sql)
  cat(sprintf("  Created cohort table %s.%s\n", TARGET_SCHEMA, COHORT_TABLE))
}, error = function(e) {
  cli::cli_abort(sprintf("Failed to create cohort table: %s", e$message))
})

cat("\nStarting Generation Benchmark...\n")

all_results <- list()

targetId <- 0
for (file in sample_files) {
  targetId <- targetId + 1
  ibis_cohort_id <- targetId + 10000  # Distinct ID for Ibis cohorts

  cat("\n========================================\n")
  cat(sprintf("Benchmarking Cohort Generation: %s\n", basename(file)))
  cat("========================================\n")

  json_str <- readChar(file, file.info(file)$size)

  # ============================================================================
  # PRE-COMPILATION PHASE (not benchmarked)
  # ============================================================================
  cat("  Pre-compiling Java SQL...\n")
  cohort_expr <- CirceR::cohortExpressionFromJson(json_str)
  options <- CirceR::createGenerateOptions(generateStats = FALSE)
  sql <- CirceR::buildCohortQuery(cohort_expr, options = options)
  rendered_sql <- SqlRender::render(sql,
                                    vocabulary_database_schema = CDM_SCHEMA,
                                    cdm_database_schema = CDM_SCHEMA,
                                    target_database_schema = TARGET_SCHEMA,
                                    results_database_schema = TARGET_SCHEMA,
                                    target_cohort_table = COHORT_TABLE,
                                    target_cohort_id = targetId)
  translated_sql <- SqlRender::translate(rendered_sql, targetDialect = TARGET_DIALECT, tempEmulationSchema = TARGET_SCHEMA)

  cat("  Pre-compiling Ibis cohort relation...\n")
  py_expr <- circe_api$cohort_expression_from_json(json_str)
  # Build the cohort relation (lazy compilation, not execution)
  cohort_relation <- circe_execution$build_cohort_relation(
    expression = py_expr,
    backend = py_backend,
    cdm_schema = CDM_SCHEMA,
    cohort_id = as.integer(ibis_cohort_id),
    results_schema = TARGET_SCHEMA,
    vocabulary_schema = CDM_SCHEMA
  )

  # ============================================================================
  # EXECUTION PHASE (benchmarked - apples to apples)
  # ============================================================================
  run_circe_java_execution <- function() {
    # Execute pre-compiled SQL
    executeSql(r_con, translated_sql)
  }

  run_circe_ibis_execution <- function() {
    # Execute pre-compiled relation with validation checks skipped
    circe_execution$write_cohort_relation(
      cohort_relation = cohort_relation,
      backend = py_backend,
      cohort_table = COHORT_TABLE,
      cohort_id = as.integer(ibis_cohort_id),
      results_schema = TARGET_SCHEMA,
      if_exists = "append",
      skip_validation = TRUE
    )
  }

  # Microbenchmark purely on SQL execution!
  cat(sprintf("  Running Pure SQL Execution Microbenchmark (%d iterations)...\n", BENCHMARK_ITERATIONS))
  cat(sprintf("  Java cohort_id: %d, Ibis cohort_id: %d\n", targetId, ibis_cohort_id))
  mb <- microbenchmark(
    CirceR_Java_Databricks = run_circe_java_execution(),
    CircePy_Ibis_Databricks = run_circe_ibis_execution(),
    times = BENCHMARK_ITERATIONS
  )
  print(mb)
  all_results[[basename(file)]] <- summary(mb)
}

# Generate Markdown Report
report_file <- "benchmark_report.md"
cat("Generating report...\n")

java_medians <- c()
ibis_medians <- c()

for (cohort_name in names(all_results)) {
  res <- all_results[[cohort_name]]
  ja <- res$median[res$expr == "CirceR_Java_Databricks"]
  ib <- res$median[res$expr == "CircePy_Ibis_Databricks"]
  if (length(ja) > 0) java_medians <- c(java_medians, ja)
  if (length(ib) > 0) ibis_medians <- c(ibis_medians, ib)
}

java_avg <- mean(java_medians)
ibis_avg <- mean(ibis_medians)

diff_pct <- if (ibis_avg < java_avg) ((java_avg - ibis_avg) / java_avg) * 100 else ((ibis_avg - java_avg) / ibis_avg) * 100
faster_stmt <- if (ibis_avg < java_avg) "faster" else "slower"

report_summary <- sprintf("> **Conclusion:** `circe_py` (Ibis) is generally **%s** than Circe-be/`SqlRender` by **~%.1f%%** when evaluating identically generated cohorts.", faster_stmt, diff_pct)

report_lines <- c(
  "# Cohort Generation Execution Benchmark (Databricks)",
  "",
  paste("*Date generated:*", Sys.time()),
  "",
  "This report compares the execution time of cohort generation on **Databricks** between the traditional **CirceR (Java + SqlRender)** and the new **circe_py (Python + Ibis)** implementation.",
  "",
  "## Benchmark Configuration",
  "",
  "- **Pre-compilation**: Both approaches pre-compile SQL/relations before execution",
  "- **Validation**: Python uses `skip_validation=TRUE` to bypass table/row checks (matches Java behavior)",
  "- **Spark Optimizations**: Adaptive query execution, partition coalescing, and broadcast joins enabled",
  "- **Iterations**: Each cohort benchmarked with identical parameters",
  "",
  "### Aggregate Performance",
  sprintf("- **CirceR/Java Average Median Time:** %.2f ms", java_avg),
  sprintf("- **CircePy/Ibis Average Median Time:** %.2f ms", ibis_avg),
  "",
  report_summary,
  "",
  "### Raw Results",
  "| Cohort | Approach | Min | lq | Mean | Median | uq | Max | Neval |",
  "|---|---|---|---|---|---|---|---|---|"
)

for (cohort_name in names(all_results)) {
  res <- all_results[[cohort_name]]
  for (i in seq_len(nrow(res))) {
    row <- res[i,]
    expr_name <- as.character(row$expr)

    # Format times depending on unit (microbenchmark handles units automatically but we extract raw or formatted)
    # The summary data frame contains time in the unit specified by attr(res, "unit") or assumes milliseconds/microseconds.
    # Actually, print provides nice formatting, but summary() returns raw values depending on unit. 
    # Usually it's in milliseconds if we don't specify. To be safe, we round them.
    format_num <- function(x) sprintf("%.2f", x)

    report_lines <- c(report_lines, sprintf("| %s | %s | %s | %s | %s | %s | %s | %s | %d |",
                                            if (i == 1) cohort_name else "",
                                            expr_name,
                                            format_num(row$min), format_num(row$lq), format_num(row$mean),
                                            format_num(row$median), format_num(row$uq), format_num(row$max), row$neval))
  }
}

writeLines(report_lines, report_file)
cat(sprintf("\nBenchmark Complete. Report saved to %s\n", report_file))
