#!/usr/bin/env Rscript
# benchmark_run_r.R
#
# R CohortGenerator benchmark — PhenotypeLibrary on Eunomia (DuckDB) or Databricks.
#
# Usage:
#   Rscript benchmarks/benchmark_run_r.R                     # DuckDB (default)
#   Rscript benchmarks/benchmark_run_r.R --backend databricks
#
# Output (in benchmark_output/):
#   r_checksum_times.csv  -- per-phenotype generation timing from checksum table

suppressPackageStartupMessages({
  library(CohortGenerator)
  library(Eunomia)
  library(DatabaseConnector)
  library(PhenotypeLibrary)
  library(dplyr)
})

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
backend <- "duckdb"
if ("--backend" %in% args) {
  idx <- which(args == "--backend")
  if (idx < length(args)) backend <- args[idx + 1]
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
script_path <- normalizePath(sub("--file=", "", commandArgs()[grep("--file=", commandArgs())]))
REPO_ROOT  <- dirname(dirname(script_path))
OUTPUT_DIR <- file.path(REPO_ROOT, "benchmark_output")
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)

EUNOMIA_DATA_DIR <- file.path(REPO_ROOT, "eunomia_data")
dir.create(EUNOMIA_DATA_DIR, showWarnings = FALSE, recursive = TRUE)
Sys.setenv(EUNOMIA_DATA_FOLDER = EUNOMIA_DATA_DIR)

DUCKDB_PATH <- file.path(OUTPUT_DIR, "eunomia.duckdb")

# ---------------------------------------------------------------------------
# 1. Load phenotype definitions from PhenotypeLibrary
# ---------------------------------------------------------------------------
cat("Loading phenotypes from PhenotypeLibrary...\n")
phenotype_log <- PhenotypeLibrary::getPhenotypeLog()
cds <- PhenotypeLibrary::getPlCohortDefinitionSet(cohortIds = phenotype_log$cohortId)
cat(sprintf("  Loaded %d phenotype definitions\n", nrow(cds)))

# ---------------------------------------------------------------------------
# 2. Set up database connection
# ---------------------------------------------------------------------------
if (backend == "duckdb") {

  cat("Setting up Eunomia DuckDB...\n")
  if (!file.exists(DUCKDB_PATH)) {
    dbPath <- Eunomia::getDatabaseFile(
      datasetName = "GiBleed",
      dbms = "duckdb",
      databaseFile = DUCKDB_PATH
    )
  } else {
    dbPath <- DUCKDB_PATH
  }
  cat(sprintf("  Database: %s\n", dbPath))

  connectionDetails <- DatabaseConnector::createConnectionDetails(
    dbms = "duckdb",
    server = dbPath
  )
  CDM_SCHEMA <- "main"
  RESULTS_SCHEMA <- "main"
  COHORT_TABLE <- "cohort"
  TEMP_EMULATION_SCHEMA <- NULL

} else if (backend == "databricks") {

  cat("Setting up Databricks connection...\n")

  # Read YAML config
  config_path <- file.path(dirname(script_path), "benchmark_db_config.yaml")
  if (!file.exists(config_path)) {
    stop(sprintf("Config not found: %s", config_path))
  }

  # Simple YAML reader — extracts top-level key's connection block
  yaml_txt <- readLines(config_path, warn = FALSE)
  yaml_txt <- yaml_txt[!grepl("^\\s*#", yaml_txt)]  # strip comments

  extract_yaml <- function(key) {
    pattern <- sprintf("^\\s*%s\\s*:\\s*[\"']?(.+?)[\"']?\\s*$", key)
    line <- grep(pattern, yaml_txt, value = TRUE)
    if (length(line) == 0) return("")
    sub(pattern, "\\1", line[1])
  }

  resolve_env <- function(val) {
    # Expand ${VAR} placeholders
    gsub("\\$\\{(\\w+)\\}", function(m) {
      v <- Sys.getenv(gsub("[${}]", "", m), unset = "")
      v
    }, val, perl = TRUE)
  }

  server_hostname <- resolve_env(extract_yaml("server_hostname"))
  http_path       <- resolve_env(extract_yaml("http_path"))
  databricks_token <- resolve_env(extract_yaml("personal_access_token"))

  if (server_hostname == "" || http_path == "" || databricks_token == "") {
    stop("Databricks credentials not found. Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN environment variables.")
  }

  CDM_SCHEMA <- resolve_env(extract_yaml("cdm_schema"))
  if (CDM_SCHEMA == "") CDM_SCHEMA <- "hive_metastore.omop_cdm"

  RESULTS_SCHEMA <- resolve_env(extract_yaml("results_schema"))
  if (RESULTS_SCHEMA == "") RESULTS_SCHEMA <- "hive_metastore.results"

  COHORT_TABLE <- "cohort_r"
  TEMP_EMULATION_SCHEMA <- RESULTS_SCHEMA  # Databricks needs a real schema for temp

  conn_string <- paste0(
    "jdbc:databricks://", server_hostname, ":443/default;",
    "transportMode=http;ssl=1;",
    "httpPath=", http_path, ";",
    "AuthMech=3;UID=token;PWD=", databricks_token
  )
  connectionDetails <- DatabaseConnector::createConnectionDetails(
    dbms = "spark", connectionString = conn_string
  )

  cat(sprintf("Databricks host: %s\n", server_hostname))

} else {
  stop(sprintf("Unknown backend: %s. Use 'duckdb' or 'databricks'.", backend))
}

cat(sprintf("CDM schema     : %s\n", CDM_SCHEMA))
cat(sprintf("Results schema : %s\n", RESULTS_SCHEMA))
cat(sprintf("Cohort table   : %s\n", COHORT_TABLE))

# ---------------------------------------------------------------------------
# 3. Generate cohorts using runCohortGeneration (incremental mode)
# ---------------------------------------------------------------------------
cat("Generating cohorts (incremental)...\n")
CohortGenerator::runCohortGeneration(
  connectionDetails = connectionDetails,
  cdmDatabaseSchema = CDM_SCHEMA,
  cohortDatabaseSchema = RESULTS_SCHEMA,
  tempEmulationSchema = TEMP_EMULATION_SCHEMA,
  cohortDefinitionSet = cds,
  incremental = TRUE,
  outputFolder = OUTPUT_DIR,
  databaseId = backend,
  stopOnError = FALSE
)

# ---------------------------------------------------------------------------
# 4. Extract timing from checksum table
# ---------------------------------------------------------------------------
cat("Extracting checksum timing...\n")
checksums <- CohortGenerator::getLastGeneratedCohortChecksums(
  connectionDetails = connectionDetails,
  cohortDatabaseSchema = RESULTS_SCHEMA
)

times <- checksums %>%
  transmute(
    cohort_definition_id = cohortDefinitionId,
    checksum = checksum,
    generation_seconds = as.numeric(difftime(endTime, startTime, units = "secs")),
    start_time = startTime,
    end_time = endTime
  )

out_file <- file.path(OUTPUT_DIR, "r_checksum_times.csv")
write.csv(times, out_file, row.names = FALSE)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
cat(sprintf("\n%s\n", paste(rep("=", 55), collapse = "")))
cat(sprintf("R benchmark complete  (backend=%s)\n", backend))
cat(sprintf("  Phenotypes loaded : %d\n", nrow(cds)))
cat(sprintf("  Cohorts generated : %d\n", nrow(times)))
cat(sprintf("  Total time (sum)  : %.4fs\n", sum(times$generation_seconds, na.rm = TRUE)))
cat(sprintf("  Times written to  : %s\n", out_file))
cat(sprintf("%s\n\n", paste(rep("=", 55), collapse = "")))
