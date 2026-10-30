# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [Unreleased]

### Added
- Registry tables now store only a definition checksum and completion marker
  (`completed`, `row_count`, `completed_at`); full definition JSON and SQL text
  are no longer written, so registry inserts stay small across data sources.
- Per-cohort completion persistence. Each cohort is marked complete in the
  registry immediately after its rows are written, so interrupted/long-running
  shards resume from the last completed cohort instead of restarting the whole
  shard. Registry writes use a short-lived reconnected connection per write,
  retry with backoff, and surface the original backend error in `ShardingError`.
- Optional cohort `family` tags and family-aware sharding. Families stay on one
  worker; `--shards`/`--max-workers` split them across processes writing to the
  same target table. `--plan-shards` emits a manifest for Databricks Workflows
  or Prefect fan-out. Shards use independent registry tables, pre-create the
  shared target/session tables, and retry failed shards.
- Runner writes now preserve unrelated cohorts on non-transactional backends by
  staging each cohort and applying a cohort-scoped delete/insert; the full cohort
  table is no longer rewritten. Definition registry entries carry a completion
  marker and row count, so partial or interrupted generations are regenerated.
- Writing cohort/session/oracle tables into the CDM schema now emits a warning;
  runner and oracle APIs document scratch-schema usage.
- CI now runs on every pull request and includes Prefect compatibility and Docker
  image smoke jobs.
- Prefect-compatible cohort-generation runner (`circe.runner`) and Docker image
  (`docker/prefect/`). The runner accepts a JSON payload with CDM/target
  schemas, table names, definition paths and backend connection; it uses the
  shared-checkpoint generator, persists definitions in a registry table, and
  reuses cohorts whose definition and target rows are unchanged.
- Legacy CohortGenerator cohort-definition loading from `Cohorts.csv`,
  `cohorts/*.json` and `sql/sql_server/*.sql` (`load_cohort_definition_set`).
  JSON is authoritative, SQL is retained in memory, and R's `stringi` /
  `SqlRender` string handling is mirrored for headers, file stems and
  transliteration. Legacy SQL can be executed as an oracle and compared with
  shared or stand-alone cohort generation (`verify_against_legacy_sql`).
- Decomposable cohort sets: `decompose_cohort_set()` recovers shared bases plus
  v1-placed refinements (additional criteria, inclusion rules, limits, end
  strategy, censoring, censor window, collapse, added concept sets) and
  `Decomposition.flatten()` reconstructs stand-alone definitions.
- Shared-checkpoint batch generation via `generate_cohort_set(..., shared=True)`.
  Primary events, qualified events and inclusion-rule matches are keyed by
  canonicalised content and materialised once, so refinement-heavy definition
  sets avoid repeating entry-population work. Concept-set ids are canonicalised
  by content, allowing cohorts with different local ids to share checkpoints.
  Tail stages reuse the existing engine functions, keeping cohort rows identical
  to the stand-alone path.
- `benchmarks/decomposable_cohorts.py` performance harness comparing shared and
  stand-alone batch generation on a synthetic DuckDB CDM, and
  `benchmarks/decomposable_cohorts_postgres.py` for an existing PostgreSQL OMOP
  CDM with two-way `EXCEPT ALL` verification.
- Cross-dialect and live database tests covering the HADES platform matrix
  (PostgreSQL, SQL Server, Redshift, SQLite, DuckDB, IRIS, Snowflake, Spark,
  Synapse and BigQuery; Oracle is excluded as a legacy target).  The suite
  checks rendered and Ibis-compiled cohort SQL for every platform and runs a
  backend-agnostic execution contract against DuckDB, PostgreSQL and SQL Server
  in CI.  See `docs/developer/database-testing.rst`.
- `ibis-mssql`, `ibis-snowflake` and `ibis-bigquery` optional dependency groups.

### Fixed
- Pinned `duckdb<2.0.0`; duckdb 2.0 removed `DuckDBPyConnection.fetch_arrow_table`,
  which ibis-framework 12.0.0 still calls internally and which the dependency
  resolver was picking up in CI.
- Databricks ibis connections no longer fail on workspaces without a
  `hive_metastore` catalog (ibis issue #11598). The post-connect workaround now
  applies to ibis >= 10 (including 12.0.0), recognizes missing-catalog errors
  that omit the SQL text, and the new `connect_databricks()` helper installs it
  before `_post_connect()` runs.
- SQL Server execution now avoids Ibis' MSSQL `overwrite=True` rename path,
  which leaves the table outside the target schema because SQL Server's
  `sp_rename` does not accept a schema-qualified new name.

## [0.3.0] - 2026-10-06

### Added
- Experimental Ibis execution engine for building and writing cohorts as relational expressions (`build_cohort()`, `write_cohort()`)
- Custom era end strategy (`CustomEraStrategy`) in the Ibis execution engine, with parity to Java CIRCE-BE
- Episode criteria (`Episode`, `EpisodeSqlBuilder`) with nested criteria, print-friendly rendering, Ibis execution support, and check-framework integration (synced with Java CIRCE-BE)
- Custom era criteria (`CustomEra`, `CustomEraSqlBuilder`) with nested criteria, print-friendly rendering, and check-framework integration (synced with Java CIRCE-BE)
- SQL rendering and dialect translation module (`circe.sqlrender`) supporting Oracle, PostgreSQL, DuckDB, BigQuery, Spark, Hive, Impala, SQL Server, SQLite, SQLite extended, Synapse, Redshift, Snowflake, Netezza, PDW, and IRIS dialects
- Cohort definition set batch generation (`CohortDefinitionSet`, `generate_cohort_set()`) with checksum-based incremental skipping
- CDM extension registration system with `@criteria_class`, `@sql_builder`, and `@markdown_template` decorators
- Waveform extension (WaveformOccurrence, WaveformFeature, WaveformRegistry, WaveformChannelMetadata) as a reference extension
- Support for snake_case YAML cohort definitions via `cohort_expression_from_yaml()`
- Persistent caching of concept set resolution in the IBIS execution layer
- `load_expression()` helper for loading cohort expressions from JSON, YAML, dict, or file paths
- Local CI preflight harness (`scripts/ci_preflight.py`) that reproduces the GitHub Actions lint, dependency-drift, and coverage gates
- Session-activity registry (`_circe_session`) with `check_stale_sessions()` / `cleanup_stale_sessions()` to detect and reclaim staging tables left behind by interrupted builds

### Fixed
- ERA collapse ordering made deterministic across repeated executions
- Collapse tie handling aligned with Java CIRCE-BE semantics
- Era filter semantics restored with correct observation filtering
- Nested correlated criteria now correctly applied within criteria groups
- Custom era strategy now honors `days_supply_override` in both the SQL builder and Ibis execution engine
- Package now importable without ibis installed
- Pydantic deprecation warnings resolved
- Pinned `sqlglot<30.18.0`; 30.18.0 regresses `DROP` rendering and breaks Ibis create-table overwrites
- `ConceptSetExpressionQueryBuilder` no longer generates the invalid `ILEFT JOIN` alias when a concept set contains excluded items; the include template now ends with a newline, matching Java CIRCE-BE's `conceptSetInclude.sql`
- Ibis execution engine: concept sets with both `includeDescendants` and `includeMapped` now resolve mapped concepts over the descendant set, and direct-only concept sets honor overlapping exclusions
- Ibis execution engine: `vocabulary_schema` defaults to `cdm_schema` during concept expansion, builds use a unique per-build prefix, and the compiled correlated-criteria cache is scoped to the execution context
- Batch generation and `write_cohort()` now drop their session staging/codeset tables (including on the `stop_on_error` raise path), and the wheel bundles the print-friendly Jinja templates

### Changed
- Dropped Python 3.8/3.9 support (minimum version is now 3.10)
- Added PyYAML as a core dependency
- Added `ibis-postgres` and `ibis-databricks` optional dependency groups (`ibis-framework[duckdb]` is a core dependency)
- Distribution renamed to `ohdsi-circepy`. Older releases remain available under the legacy `ohdsi-circe-python-alpha` name (to be retired later); the `ohdsi-circe` name on PyPI belongs to an unrelated project

## [0.2.0] - 2026-02-25

### Added
- Helper functions for altering cohort objects in consistent ways (enforcing first event, prior observation period, etc.)
- Default behaviour of circe models is now better with empty lists (consistent with Java implementation)
- Additional validation checks for cohort expression objects

## [0.1.0] - 2026-01-23

### Added
- Initial Alpha Release of the CIRCE Python implementation.
- Full parity with OHDSI CIRCE-BE Java library for cohort definition and SQL generation.
- Expanded test suite with 3,400+ tests including parity checks.
- Comprehensive documentation and GitHub Actions release workflows.