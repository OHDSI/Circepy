#!/usr/bin/env Rscript
# benchmark_run_r.R
#
# R CohortGenerator benchmark against a Databricks SQL warehouse.
# Runs independently of benchmark_run_python.py — no shared DuckDB file.
#
# What this script does:
#   1. Loads cohort definitions from OHDSI PhenotypeLibrary
#   2. Connects to Databricks using credentials from .Renviron
#   3. Runs CohortGenerator::generateCohortSet() and writes rows to
#      {DATABRICKS_SCRATCH_SCHEMA}.cohort_r
#   4. Writes per-cohort timing and status to benchmark_output/r_results.csv
#
# Prerequisites:
#   Fill in .Renviron (repo root) with:
#     DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN, DATABRICKS_SCRATCH_SCHEMA
#   The Databricks JDBC driver JAR must be available:
#     Download from https://www.databricks.com/spark/jdbc-drivers-download
#     and set DATABASECONNECTOR_JAR_FOLDER in .Renviron to its directory.
#   CDM data must exist at healthverity_cc.cdm_healthverity_cc_all_v3910
#
# Usage:
#   Rscript examples/benchmark_run_r.R
#
# Output files (in benchmark_output/):
#   r_results.csv  -- per-cohort timing and status

suppressPackageStartupMessages({
  library(dplyr)
  library(PhenotypeLibrary)
  library(CohortGenerator)
  library(DatabaseConnector)
})

# ---------------------------------------------------------------------------
# Paths and credentials
# ---------------------------------------------------------------------------
script_path <- normalizePath(
  sub("--file=", "", grep("--file=", commandArgs(trailingOnly = FALSE), value = TRUE)[1])
)
REPO_ROOT  <- dirname(dirname(script_path))   # examples/ -> repo root
OUTPUT_DIR <- file.path(REPO_ROOT, "benchmark_output")
if (!dir.exists(OUTPUT_DIR)) dir.create(OUTPUT_DIR, recursive = TRUE)

# Load .Renviron from the repo root (supplements the user-level ~/.Renviron)
renviron_path <- file.path(REPO_ROOT, ".Renviron")
if (file.exists(renviron_path)) readRenviron(renviron_path)

R_RESULTS_CSV <- file.path(OUTPUT_DIR, "r_results.csv")

DB_HOST         <- Sys.getenv("DATABRICKS_HOST")
DB_HTTP_PATH    <- Sys.getenv("DATABRICKS_HTTP_PATH")
DB_TOKEN        <- Sys.getenv("DATABRICKS_TOKEN")
SCRATCH_SCHEMA  <- Sys.getenv("DATABRICKS_SCRATCH_SCHEMA")
CDM_SCHEMA      <- "healthverity_cc.cdm_healthverity_cc_all_v3910"
COHORT_TABLE    <- "cohort_r"

for (var in c("DB_HOST", "DB_HTTP_PATH", "DB_TOKEN", "SCRATCH_SCHEMA")) {
  if (get(var) == "") stop(sprintf("Environment variable %s is not set. Check .Renviron.", var))
}

cat(sprintf("Databricks host  : %s\n", DB_HOST))
cat(sprintf("CDM schema       : %s\n", CDM_SCHEMA))
cat(sprintf("Cohort schema    : %s\n", SCRATCH_SCHEMA))
cat(sprintf("Output directory : %s\n", OUTPUT_DIR))

# ---------------------------------------------------------------------------
# 1. Load PhenotypeLibrary
# ---------------------------------------------------------------------------
cat("\nLoading OHDSI PhenotypeLibrary...\n")
phenotype_log <- PhenotypeLibrary::getPhenotypeLog()
all_ids <- phenotype_log$cohortId
cat(sprintf("  %d cohort IDs found in phenotype log\n", length(all_ids)))

cds <- PhenotypeLibrary::getPlCohortDefinitionSet(cohortIds = all_ids[1:40])
cat(sprintf("  %d cohort definitions loaded (first 40)\n", nrow(cds)))

# ---------------------------------------------------------------------------
# 2. Connect to Databricks
# ---------------------------------------------------------------------------
cat("\nConnecting to Databricks...\n")
conn_string <- paste0(
  "jdbc:databricks://", DB_HOST, ":443/default;",
  "transportMode=http;ssl=1;",
  "httpPath=", DB_HTTP_PATH, ";",
  "AuthMech=3;UID=token;PWD=", DB_TOKEN
)
conn_details <- DatabaseConnector::createConnectionDetails(
  dbms             = "spark",
  connectionString = conn_string
)

# Verify connection and CDM access
conn_check <- DatabaseConnector::connect(conn_details)
tryCatch({
  test <- DatabaseConnector::querySql(
    conn_check,
    sprintf("SELECT COUNT(*) AS n FROM %s.person", CDM_SCHEMA)
  )
  cat(sprintf("  CDM verified: %s.person has %d rows\n", CDM_SCHEMA, test$n))
}, error = function(e) {
  DatabaseConnector::disconnect(conn_check)
  stop(sprintf("Cannot access CDM at %s: %s", CDM_SCHEMA, conditionMessage(e)))
})
DatabaseConnector::disconnect(conn_check)

# ---------------------------------------------------------------------------
# 3. Create cohort tables (idempotent — drops and recreates)
# ---------------------------------------------------------------------------
cat("\nCreating cohort tables in", SCRATCH_SCHEMA, "...\n")
cohort_table_names <- CohortGenerator::getCohortTableNames(cohortTable = COHORT_TABLE)

# Drop existing tables for a clean run
conn_drop <- DatabaseConnector::connect(conn_details)
for (tbl in unlist(cohort_table_names)) {
  tryCatch(
    DatabaseConnector::executeSql(
      conn_drop,
      sprintf("DROP TABLE IF EXISTS %s.%s", SCRATCH_SCHEMA, tbl),
      reportOverallTime = FALSE
    ),
    error = function(e) NULL
  )
}
DatabaseConnector::disconnect(conn_drop)

CohortGenerator::createCohortTables(
  connectionDetails    = conn_details,
  cohortDatabaseSchema = SCRATCH_SCHEMA,
  cohortTableNames     = cohort_table_names,
  incremental          = FALSE
)

# ---------------------------------------------------------------------------
# 4. Generate cohorts — single persistent connection
# ---------------------------------------------------------------------------
cat(sprintf("\nGenerating %d cohorts with R CohortGenerator...\n", nrow(cds)))

all_stats <- NULL
t_start   <- proc.time()
n_cohorts <- nrow(cds)

# One connection for the entire run — avoids per-cohort reconnection overhead.
global_conn <- DatabaseConnector::connect(conn_details)

for (cohort_i in seq_len(n_cohorts)) {
  one_cds <- cds[cohort_i, ]

  # SqlRender (spark dialect) materialises #temp tables as real tables in
  # tempEmulationSchema. Drop them before each cohort so they don't conflict.
  for (tmp_tbl in c("Codesets", "qualified_events", "inclusion_events",
                    "included_events", "inclusion_rules", "best_events",
                    "cohort_rows", "final_cohort",
                    paste0("Inclusion_", 0:20))) {
    tryCatch(
      DatabaseConnector::executeSql(
        global_conn,
        sprintf("DROP TABLE IF EXISTS %s.%s", SCRATCH_SCHEMA, tmp_tbl),
        reportOverallTime = FALSE
      ),
      error = function(e) NULL
    )
  }

  cohort_stats <- tryCatch(
    CohortGenerator::generateCohortSet(
      connection           = global_conn,
      cdmDatabaseSchema    = CDM_SCHEMA,
      cohortDatabaseSchema = SCRATCH_SCHEMA,
      tempEmulationSchema  = SCRATCH_SCHEMA,
      cohortTableNames     = cohort_table_names,
      cohortDefinitionSet  = one_cds,
      stopOnError          = FALSE,
      incremental          = FALSE
    ),
    error = function(e) {
      cat(sprintf("  Cohort %d/%d error: %s\n", cohort_i, n_cohorts, conditionMessage(e)))
      NULL
    }
  )

  if (!is.null(cohort_stats)) {
    all_stats <- if (is.null(all_stats)) cohort_stats else rbind(all_stats, cohort_stats)
  }

  cat(sprintf("  %d/%d cohorts processed\n", cohort_i, n_cohorts))
}

DatabaseConnector::disconnect(global_conn)

generation_stats <- all_stats
elapsed <- (proc.time() - t_start)[["elapsed"]]
cat(sprintf("  Done in %.1f seconds\n", elapsed))

# ---------------------------------------------------------------------------
# 5. Summarise and write results
# ---------------------------------------------------------------------------
conn <- DatabaseConnector::connect(conn_details)
cohort_counts <- DatabaseConnector::querySql(
  conn,
  sprintf(
    "SELECT cohort_definition_id, COUNT(*) AS row_count FROM %s.%s GROUP BY 1",
    SCRATCH_SCHEMA, COHORT_TABLE
  )
)
DatabaseConnector::disconnect(conn)

results <- generation_stats %>%
  left_join(cohort_counts, by = c("cohortId" = "cohort_definition_id")) %>%
  mutate(
    row_count          = coalesce(row_count, 0L),
    generation_seconds = as.numeric(endTime - startTime, units = "secs"),
    status             = generationStatus
  ) %>%
  select(cohortId, cohortName, status, generation_seconds, row_count)

write.csv(results, R_RESULTS_CSV, row.names = FALSE)

n_complete <- sum(results$status == "COMPLETE")
n_failed   <- sum(results$status == "FAILED")
cat(sprintf("\nR benchmark complete\n"))
cat(sprintf("  COMPLETE : %d\n", n_complete))
cat(sprintf("  FAILED   : %d\n", n_failed))
cat(sprintf("  Total rows in %s : %d\n", COHORT_TABLE, sum(results$row_count)))
cat(sprintf("  Results written to %s\n", R_RESULTS_CSV))
