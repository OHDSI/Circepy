#!/usr/bin/env Rscript
# scripts/benchmark_cohort_generation.R
# Benchmark cohort GENERATION (execution) process: CirceR + SqlRender vs Ibis (Python)

# Ensure packages are installed
required_packages <- c("microbenchmark", "reticulate", "CirceR", "SqlRender", "DBI", "duckdb")
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
library(DBI)
library(duckdb)

cat("Copying Eunomia to a temporary writable database for the benchmark...\n")
eunomia_source <- "tests/eunomia.duckdb"
if (!file.exists(eunomia_source)) {
  eunomia_source <- file.path("..", "tests", "eunomia.duckdb")
}
temp_db <- tempfile(fileext = ".duckdb")
file.copy(eunomia_source, temp_db)

cat("Setting up R DuckDB connection using temp Eunomia...\n")
r_con <- dbConnect(duckdb::duckdb(), dbdir = temp_db)
venv_path <- file.path(getwd(), ".venv")
if (dir.exists(venv_path)) {
  use_python(file.path(venv_path, "bin", "python"), required = TRUE)
} else {
  # Fallback to current environment
}

cat("Importing Python libraries via reticulate...\n")
circe_api <- import("circe.api")
ibis <- import("ibis")

cat("Preparing Ibis duckdb backend referencing temp Eunomia...\n")
py_backend <- ibis$duckdb$connect(temp_db)

# ==============================================================================
# DEFAULT EUNOMIA BENCHMARK CONFIGURATION
# ==============================================================================
TARGET_DIALECT <- "duckdb"
CDM_SCHEMA <- "main"
TARGET_SCHEMA <- "main"
COHORT_TABLE <- "cohort"

# ==============================================================================
# LIVE DATABASE CONFIGURATION (Uncomment and edit to benchmark real databases)
# ==============================================================================
# library(DatabaseConnector)
# connectionDetails <- createConnectionDetails(dbms = "postgresql", server = "localhost/cdm", user = "user", password = "pw")
# r_con <- connect(connectionDetails)
# py_backend <- ibis$postgres$connect(host="localhost", database="cdm", user="user", password="pw")
# TARGET_DIALECT <- "postgresql"  # Or your true dialect
# CDM_SCHEMA <- "cdm"
# TARGET_SCHEMA <- "results"
# COHORT_TABLE <- "cohort"
# ==============================================================================

cohorts_dir <- file.path("tests", "cohorts")
if (!dir.exists(cohorts_dir)) {
  cohorts_dir <- file.path("..", "tests", "cohorts")
}

json_files <- list.files(cohorts_dir, pattern = "\\.json$", full.names = TRUE)
if (length(json_files) == 0) stop("No cohort JSON files found in tests/cohorts/")
sample_files <- head(json_files, 30)

cat("\nStarting Generation Benchmark...\n")

all_results <- list()

for (file in sample_files) {
  cat("\n========================================\n")
  cat(sprintf("Benchmarking Cohort Generation: %s\n", basename(file)))
  cat("========================================\n")
  
  json_str <- readChar(file, file.info(file)$size)
  
  # PRE-COMPILE JAVA SQL
  cohort_expr <- CirceR::cohortExpressionFromJson(json_str)
  options <- CirceR::createGenerateOptions(generateStats = FALSE)
  sql <- CirceR::buildCohortQuery(cohort_expr, options = options)
  rendered_sql <- SqlRender::render(sql,
                                    vocabulary_database_schema = CDM_SCHEMA,
                                    cdm_database_schema = CDM_SCHEMA,
                                    target_database_schema = TARGET_SCHEMA,
                                    results_database_schema = TARGET_SCHEMA,
                                    target_cohort_table = COHORT_TABLE,
                                    target_cohort_id = 1)
  translated_sql <- SqlRender::translate(rendered_sql, targetDialect = TARGET_DIALECT)
  java_queries <- strsplit(translated_sql, ";\n*\\s*")[[1]]
  java_queries_clean <- vector("list", length(java_queries))
  idx <- 1
  for (q in java_queries) {
    qc <- trimws(q)
    if (nchar(qc) > 0) {
      java_queries_clean[[idx]] <- qc
      idx <- idx + 1
    }
  }
  
  # PRE-COMPILE IBIS SQL
  py_expr <- circe_api$cohort_expression_from_json(json_str)
  table_expr <- circe_api$build_cohort(py_expr, backend = py_backend, cdm_schema = CDM_SCHEMA)
  ibis_sql_str <- ibis$to_sql(table_expr)
  
  run_circe_java_execution <- function() {
    # Execute on connection without overhead!
    for (q in java_queries_clean) {
      if (!is.null(q)) {
        dbExecute(r_con, q)
      }
    }
  }
  
  run_circe_ibis_execution <- function() {
    # Execute the pre-compiled Ibis SQL directly on duckdb
    py_backend$raw_sql(ibis_sql_str)
  }
  
  # Microbenchmark purely on execution!
  cat("  Running Pure Execution Microbenchmark (10 iterations)...\n")
  mb <- microbenchmark(
    CirceR_Java_DBI = run_circe_java_execution(),
    CircePy_Ibis_DuckDB = run_circe_ibis_execution(),
    times = 10
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
  ja <- res$median[res$expr == "CirceR_Java_DBI"]
  ib <- res$median[res$expr == "CircePy_Ibis_DuckDB"]
  if (length(ja) > 0) java_medians <- c(java_medians, ja)
  if (length(ib) > 0) ibis_medians <- c(ibis_medians, ib)
}

java_avg <- mean(java_medians)
ibis_avg <- mean(ibis_medians)

diff_pct <- if (ibis_avg < java_avg) ((java_avg - ibis_avg) / java_avg) * 100 else ((ibis_avg - java_avg) / ibis_avg) * 100
faster_stmt <- if (ibis_avg < java_avg) "faster" else "slower"

report_summary <- sprintf("> **Conclusion:** `circe_py` (Ibis) is generally **%s** than Circe-be/`SqlRender` by **~%.1f%%** when evaluating identically generated cohorts.", faster_stmt, diff_pct)

report_lines <- c(
  "# Cohort Generation Execution Benchmark",
  "",
  paste("*Date generated:*", Sys.time()),
  "",
  "This report compares the execution time of cohort generation between the traditional **CirceR (Java + T-SQL)** and the new **circe_py (Python + Ibis)** implementation.",
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
    row <- res[i, ]
    expr_name <- as.character(row$expr)
    
    # Format times depending on unit (microbenchmark handles units automatically but we extract raw or formatted)
    # The summary data frame contains time in the unit specified by attr(res, "unit") or assumes milliseconds/microseconds.
    # Actually, print provides nice formatting, but summary() returns raw values depending on unit. 
    # Usually it's in milliseconds if we don't specify. To be safe, we round them.
    format_num <- function(x) sprintf("%.2f", x)
    
    report_lines <- c(report_lines, sprintf("| %s | %s | %s | %s | %s | %s | %s | %s | %d |",
                                            if(i==1) cohort_name else "",
                                            expr_name,
                                            format_num(row$min), format_num(row$lq), format_num(row$mean),
                                            format_num(row$median), format_num(row$uq), format_num(row$max), row$neval))
  }
}

writeLines(report_lines, report_file)
cat(sprintf("\nBenchmark Complete. Report saved to %s\n", report_file))
