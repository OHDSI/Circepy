# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [0.3.0] - 2026-07-10

### Added
- Experimental Ibis execution engine for building and writing cohorts as relational expressions (`build_cohort()`, `write_cohort()`)
- Support for snake_case YAML cohort definitions via `cohort_expression_from_yaml()`
- Persistent caching of concept set resolution in the IBIS execution layer
- `load_expression()` helper for loading cohort expressions from JSON, YAML, dict, or file paths

### Fixed
- ERA collapse ordering made deterministic across repeated executions
- Collapse tie handling aligned with Java CIRCE-BE semantics
- Era filter semantics restored with correct observation filtering
- Nested correlated criteria now correctly applied within criteria groups
- Package now importable without ibis installed
- Pydantic deprecation warnings resolved

### Changed
- Dropped Python 3.8 support (minimum version is now 3.9)
- Added PyYAML as a core dependency
- Added `ibis`, `ibis-duckdb`, `ibis-postgres`, and `ibis-databricks` optional dependency groups

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