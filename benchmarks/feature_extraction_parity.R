#!/usr/bin/env Rscript
# Run FeatureExtraction against a Spark CDM over Hive JDBC and export the
# aggregated covariate tables as CSV.
#
# This is the reference side of the era-cache parity test. It is deliberately
# explicit: the analyses mirror the era-cache feature definitions (one
# DomainConcept analysis per condition concept) so the two counts are directly
# comparable.
#
# Usage:
#   Rscript benchmarks/feature_extraction_parity.R \
#       --cohort-table coh_201826 --cohort-id 1 --start-day -365 \
#       --output /tmp/fe_det_365
#
# Requirements:
#   - FeatureExtraction >= 3.14, DatabaseConnector, SqlRender, rJava
#   - A JDBC driver directory containing hive-jdbc-<v>-standalone.jar
#     (default HIVE_JDBC_VERSION=3.1.3, override with the env var)
#   - JVM initialised with FeatureExtraction's jars FIRST, then the JDBC jar.
#     Mixing in Spark's own jars duplicates json/slf4j/SqlRender classes and
#     breaks FeatureExtraction's Java bridge.

args <- commandArgs(trailingOnly = TRUE)
arg <- function(name, default = NULL) {
  index <- match(paste0("--", name), args)
  if (is.na(index)) default else args[index + 1]
}

cohort_table <- arg("cohort-table")
cohort_id <- as.integer(arg("cohort-id", "1"))
cohort_schema <- arg("cohort-schema", "cdm_era_cache")
cdm_schema <- arg("cdm-schema", "cdm")
start_day <- as.integer(arg("start-day", "-365"))
end_day <- as.integer(arg("end-day", "0"))
output_dir <- arg("output", "fe_output")
server <- arg("server", "jdbc:hive2://127.0.0.1:10000/default")
driver_dir <- arg("driver-dir", file.path("/tmp", paste0("jdbc_", Sys.getenv("HIVE_JDBC_VERSION", "3.1.3"))))

if (is.null(cohort_table)) stop("--cohort-table is required")

# --- JVM: FeatureExtraction jars first, then a standalone JDBC driver --------
fe_jars <- list.files(file.path(find.package("FeatureExtraction"), "java"),
                      full.names = TRUE, pattern = "[.]jar$")
jdbc_jars <- list.files(driver_dir, full.names = TRUE, pattern = "standalone[.]jar$")
if (!length(jdbc_jars)) {
  stop("No hive-jdbc-*-standalone.jar in ", driver_dir)
}
rJava::.jinit(classpath = c(fe_jars, jdbc_jars))

suppressMessages({
  library(DatabaseConnector)
  library(SqlRender)
  library(FeatureExtraction)
})

dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# --- analyses mirroring the era-cache features -------------------------------
# Keep this list in sync with FEATURES in benchmarks/fe_parity_compare.py.
features <- list(
  c(201826,  "Type 2 diabetes"),
  c(316139,  "Heart failure"),
  c(433736,  "Obesity"),
  c(317009,  "Asthma"),
  c(46271022, "Chronic kidney disease"),
  c(255573,  "COPD")
)

analyses <- lapply(seq_along(features), function(i) {
  createAnalysisDetails(
    analysisId = i,
    sqlFileName = "DomainConcept.sql",
    parameters = list(
      analysisId = i,
      analysisName = features[[i]][2],
      domainId = "Condition",
      domainTable = "condition_occurrence",
      domainConceptId = "condition_concept_id",
      domainStartDate = "condition_start_date",
      domainEndDate = "condition_end_date",
      startDay = start_day,
      endDay = end_day,
      subType = "standard",
      timePart = "day",
      timeInterval = 365,
      temporal = FALSE,
      temporalSequence = FALSE,
      aggregated = TRUE
    ),
    includedCovariateConceptIds = as.integer(features[[i]][1]),
    addDescendantsToInclude = FALSE,
    excludedCovariateConceptIds = integer(0),
    addDescendantsToExclude = FALSE,
    includedCovariateIds = numeric(0)
  )
})

settings <- createDetailedCovariateSettings(analyses = analyses)
settings$temporal <- FALSE
settings$temporalSequence <- FALSE

connection_details <- DatabaseConnector::createConnectionDetails(
  dbms = "hive",
  connectionString = server,
  user = "spark",
  password = "",
  pathToDriver = driver_dir
)

# --- run, retrying sessions that the server drops on long statements ---------
run_covariates <- function(attempts = 6) {
  for (attempt in seq_len(attempts)) {
    result <- tryCatch({
      connection <- DatabaseConnector::connect(connection_details)
      # Tag as "spark" so DatabaseConnector uses plain `execute`; hive-jdbc does
      # not implement `executeLargeUpdate`.
      attr(connection, "dbms") <- "spark"
      covariates <- getDbCovariateData(
        connection = connection,
        cdmDatabaseSchema = cdm_schema,
        cohortTable = cohort_table,
        cohortDatabaseSchema = cohort_schema,
        cohortIds = cohort_id,
        rowIdField = "subject_id",
        covariateSettings = settings,
        aggregated = TRUE
      )
      try(DatabaseConnector::disconnect(connection), silent = TRUE)
      covariates
    }, error = function(error) {
      message("attempt ", attempt, " failed: ", conditionMessage(error))
      Sys.sleep(min(10 * attempt, 60))
      NULL
    })
    if (!is.null(result)) return(result)
  }
  stop("FeatureExtraction failed after ", attempts, " attempts")
}

covariates <- run_covariates()
print(summary(covariates))

write.csv(as.data.frame(covariates$covariates),
          file.path(output_dir, "covariates.csv"), row.names = FALSE)
write.csv(as.data.frame(covariates$covariateRef),
          file.path(output_dir, "covariateRef.csv"), row.names = FALSE)
write.csv(as.data.frame(covariates$analysisRef),
          file.path(output_dir, "analysisRef.csv"), row.names = FALSE)
cat("DONE\n")
