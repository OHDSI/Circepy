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

cfg_value <- function(value, default = "") {
  if (is.null(value) || identical(value, "")) {
    return(default)
  }
  value
}

trim_quotes <- function(value) {
  sub("^(['\"])", "", sub("(['\"])$", "", trimws(value)))
}

expand_env_vars <- function(value) {
  matches <- gregexpr("\\$\\{([A-Za-z0-9_]+)\\}", value, perl = TRUE)
  tokens <- regmatches(value, matches)[[1]]
  if (length(tokens) == 0) {
    return(value)
  }

  expanded <- value
  for (token in unique(tokens)) {
    var_name <- sub("^\\$\\{", "", sub("\\}$", "", token))
    expanded <- gsub(token, Sys.getenv(var_name, unset = ""), expanded, fixed = TRUE)
  }
  expanded
}

load_databricks_config <- function(config_path) {
  if (!file.exists(config_path)) {
    stop(sprintf("Config not found: %s", config_path))
  }

  lines <- readLines(config_path, warn = FALSE)
  section_started <- FALSE
  current_group <- NULL
  values <- list()

  for (line in lines) {
    if (grepl("^\\s*$", line) || grepl("^\\s*#", line)) {
      next
    }

    if (!section_started) {
      if (grepl("^databricks:\\s*$", line)) {
        section_started <- TRUE
      }
      next
    }

    if (grepl("^[A-Za-z0-9_-]+:\\s*$", line)) {
      break
    }

    if (grepl("^  [A-Za-z0-9_-]+:\\s*$", line)) {
      current_group <- sub("^  ([A-Za-z0-9_-]+):\\s*$", "\\1", line)
      if (is.null(values[[current_group]])) {
        values[[current_group]] <- list()
      }
      next
    }

    if (grepl("^  [A-Za-z0-9_-]+:\\s*", line)) {
      key <- sub("^  ([A-Za-z0-9_-]+):.*$", "\\1", line)
      raw_value <- sub("^  [A-Za-z0-9_-]+:\\s*", "", line)
      values[[key]] <- expand_env_vars(trim_quotes(raw_value))
      current_group <- NULL
      next
    }

    if (!is.null(current_group) && grepl("^    [A-Za-z0-9_-]+:\\s*", line)) {
      key <- sub("^    ([A-Za-z0-9_-]+):.*$", "\\1", line)
      raw_value <- sub("^    [A-Za-z0-9_-]+:\\s*", "", line)
      values[[current_group]][[key]] <- expand_env_vars(trim_quotes(raw_value))
    }
  }

  values
}

# ---------------------------------------------------------------------------
# 1. Load phenotype definitions from PhenotypeLibrary
# ---------------------------------------------------------------------------
cat("Loading phenotypes from PhenotypeLibrary...\n")
phenotype_log <- PhenotypeLibrary::getPhenotypeLog()
cds <- PhenotypeLibrary::getPlCohortDefinitionSet(cohortIds = phenotype_log$cohortId)
cat(sprintf("  Loaded %d phenotype definitions\n", nrow(cds)))

# ---------------------------------------------------------------------------
# 1b. Export phenotype JSONs and manifest for the Python benchmark
# ---------------------------------------------------------------------------
cat("Exporting phenotype JSONs and manifest ...\n")
json_dir <- file.path(OUTPUT_DIR, "phenotype_jsons")
dir.create(json_dir, showWarnings = FALSE, recursive = TRUE)

for (i in seq_len(nrow(cds))) {
  cohort_id <- cds$cohortId[i]
  json_path <- file.path(json_dir, sprintf("%d.json", cohort_id))
  writeLines(cds$json[i], json_path)
}

manifest <- data.frame(
  cohortId   = cds$cohortId,
  cohortName = cds$cohortName,
  stringsAsFactors = FALSE
)
write.csv(manifest, file.path(OUTPUT_DIR, "phenotype_manifest.csv"), row.names = FALSE)
cat(sprintf("  Wrote %d JSONs and manifest\n", nrow(cds)))

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

  config_path <- file.path(dirname(script_path), "benchmark_db_config.yaml")
  cfg <- load_databricks_config(config_path)
  conn_cfg <- cfg$connection

  server_hostname <- cfg_value(conn_cfg$server_hostname)
  http_path <- cfg_value(conn_cfg$http_path)
  databricks_token <- cfg_value(conn_cfg$personal_access_token)

  if (server_hostname == "" || http_path == "" || databricks_token == "") {
    stop(
      paste(
        "Databricks credentials not found in benchmarks/benchmark_db_config.yaml.",
        "Set DATABRICKS_HOST, DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN",
        "before running the benchmarks."
      )
    )
  }

  CDM_SCHEMA <- cfg_value(cfg$cdm_schema)
  RESULTS_SCHEMA <- cfg_value(cfg$results_schema)
  VOCABULARY_SCHEMA <- cfg_value(cfg$vocabulary_schema, CDM_SCHEMA)
  if (CDM_SCHEMA == "") {
    stop("Databricks cdm_schema is required. Set DATABRICKS_CDM_SCHEMA in the environment or update the benchmark config.")
  }
  if (RESULTS_SCHEMA == "") {
    stop("Databricks results_schema is required. Set DATABRICKS_RESULTS_SCHEMA in the environment or update the benchmark config.")
  }

  COHORT_TABLE <- cfg_value(cfg$r_cohort_table, "cohort")
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
if (backend == "databricks") {
  cat(sprintf("Vocabulary schema: %s\n", VOCABULARY_SCHEMA))
}
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
