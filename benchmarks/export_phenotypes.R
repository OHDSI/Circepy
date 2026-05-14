#!/usr/bin/env Rscript
# export_phenotypes.R
#
# Export PhenotypeLibrary cohort JSONs for Python consumption.
#
# Usage:
#   Rscript benchmarks/export_phenotypes.R
#
# Output:
#   benchmark_output/phenotype_jsons/<cohortId>.json  -- one JSON per cohort
#   benchmark_output/phenotype_manifest.csv           -- cohortId, cohortName

suppressPackageStartupMessages({
  library(PhenotypeLibrary)
})

script_path <- normalizePath(sub("--file=", "", commandArgs()[grep("--file=", commandArgs())]))
REPO_ROOT  <- dirname(dirname(script_path))
OUTPUT_DIR <- file.path(REPO_ROOT, "benchmark_output")
JSON_DIR   <- file.path(OUTPUT_DIR, "phenotype_jsons")
dir.create(JSON_DIR, showWarnings = FALSE, recursive = TRUE)

cat("Loading phenotypes from PhenotypeLibrary...\n")
phenotype_log <- PhenotypeLibrary::getPhenotypeLog()
cds <- PhenotypeLibrary::getPlCohortDefinitionSet(cohortIds = phenotype_log$cohortId)
cat(sprintf("  Loaded %d phenotype definitions\n", nrow(cds)))

cat(sprintf("Writing JSONs to %s...\n", JSON_DIR))
for (i in seq_len(nrow(cds))) {
  cohort_id <- cds$cohortId[i]
  json_path <- file.path(JSON_DIR, sprintf("%d.json", cohort_id))
  writeLines(cds$json[i], json_path)
}

manifest <- data.frame(
  cohortId   = cds$cohortId,
  cohortName = cds$cohortName,
  stringsAsFactors = FALSE
)
manifest_path <- file.path(OUTPUT_DIR, "phenotype_manifest.csv")
write.csv(manifest, manifest_path, row.names = FALSE)

cat(sprintf("Wrote %d JSONs and manifest to %s\n", nrow(cds), manifest_path))
