#!/usr/bin/env Rscript
# benchmark_run_r.R
#
# R CohortGenerator benchmark — PhenotypeLibrary on Eunomia (DuckDB).
#
# Usage:
#   Rscript benchmarks/benchmark_run_r.R
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
# 2. Set up Eunomia DuckDB database
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 3. Generate cohorts using runCohortGeneration (incremental mode)
# ---------------------------------------------------------------------------
cat("Generating cohorts (incremental)...\n")
CohortGenerator::runCohortGeneration(
  connectionDetails = connectionDetails,
  cdmDatabaseSchema = "main",
  cohortDatabaseSchema = "main",
  cohortDefinitionSet = cds,
  incremental = TRUE,
  outputFolder = OUTPUT_DIR,
  databaseId = "eunomia",
  stopOnError = FALSE
)

# ---------------------------------------------------------------------------
# 4. Extract timing from checksum table
# ---------------------------------------------------------------------------
cat("Extracting checksum timing...\n")
checksums <- CohortGenerator::getLastGeneratedCohortChecksums(
  connectionDetails = connectionDetails,
  cohortDatabaseSchema = "main"
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
cat(sprintf("R benchmark complete\n"))
cat(sprintf("  Phenotypes loaded : %d\n", nrow(cds)))
cat(sprintf("  Cohorts generated : %d\n", nrow(times)))
cat(sprintf("  Total time (sum)  : %.4fs\n", sum(times$generation_seconds, na.rm = TRUE)))
cat(sprintf("  Times written to  : %s\n", out_file))
cat(sprintf("%s\n\n", paste(rep("=", 55), collapse = "")))
