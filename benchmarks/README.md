# CircePy CohortGeneration Benchmarks

R and Python benchmarks that generate OHDSI PhenotypeLibrary cohort definitions
against the Eunomia synthetic OMOP CDM (DuckDB backend). Measures per-cohort
generation time and compares R `CohortGenerator` vs Python `circe` performance.

## Prerequisites

Install the required R packages:

```r
install.packages("remotes")
remotes::install_github("OHDSI/Eunomia")
remotes::install_github("OHDSI/CohortGenerator")
remotes::install_github("OHDSI/DatabaseConnector")
remotes::install_github("OHDSI/PhenotypeLibrary")
```

Install the Python package with DuckDB support:

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# 1. Export PhenotypeLibrary cohort JSONs (one-time setup)
Rscript benchmarks/export_phenotypes.R

# 2. Run R benchmark (creates Eunomia DuckDB, generates cohorts)
Rscript benchmarks/benchmark_run_r.R

# 3. Run Python benchmark (reuses same DuckDB, generates cohorts)
python benchmarks/benchmark_run_py.py

# 4. Analyze and compare results
python benchmarks/benchmark_analyze_duckdb.py
```

## Files

| File | Language | Purpose |
|------|----------|---------|
| `export_phenotypes.R` | R | Exports PhenotypeLibrary cohort JSONs for Python consumption |
| `benchmark_run_r.R` | R | Runs R CohortGenerator against Eunomia DuckDB |
| `benchmark_run_py.py` | Python | Runs Python `generate_cohort_set()` against Eunomia DuckDB |
| `benchmark_analyze_duckdb.py` | Python | Side-by-side comparison of R vs Python timing, cross-validation |
| `benchmark_db_config.yaml` | — | Database backend configurations |

## Output

All output is written to `benchmark_output/`:

| File | Source | Description |
|------|--------|-------------|
| `eunomia.duckdb` | R | Persistent DuckDB with Eunomia GiBleed CDM |
| `phenotype_jsons/` | R export | One Circe JSON per PhenotypeLibrary cohort |
| `phenotype_manifest.csv` | R export | Cohort ID and name mapping |
| `r_checksum_times.csv` | R benchmark | Per-cohort generation timing from R |
| `py_checksum_times.csv` | Python benchmark | Per-cohort generation timing from Python |

## Incremental Mode

Both benchmarks use incremental generation. After the first run, unchanged cohorts
are skipped based on SHA-256 checksums of their definitions. Timing from the
original run is preserved in the checksum history table.
