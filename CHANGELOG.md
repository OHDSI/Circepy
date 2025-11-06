# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-11-06

### Added

- Complete cohort definition data model with Pydantic validation
- 18+ SQL builders covering all OMOP CDM domains:
  - Condition Occurrence and Condition Era
  - Drug Exposure and Drug Era
  - Procedure Occurrence
  - Measurement and Observation
  - Visit Occurrence and Visit Detail
  - Device Exposure and Specimen
  - Death, Location Region
  - Observation Period, Payer Plan Period, Dose Era
- Comprehensive CLI with four main commands:
  - `circe validate` - Validate cohort expressions
  - `circe generate-sql` - Generate SQL from cohort definitions
  - `circe render-markdown` - Render human-readable markdown
  - `circe process` - Combined validation, SQL generation, and rendering
- Java interoperability with camelCase/snake_case field name support
- Cohort expression validation with 40+ checker implementations
- Markdown rendering for print-friendly cohort descriptions
- 896 comprehensive tests achieving 71% code coverage
- High-level API functions for programmatic use
- Complete type hints with py.typed marker for IDE support

### Features

- Support for Python 3.8, 3.9, 3.10, 3.11, and 3.12
- Full OMOP CDM v5.x compatibility
- Type hints throughout the codebase
- Concept set expression handling with include/exclude logic
- Window criteria for temporal relationships
- Correlated criteria for complex cohort logic
- Date adjustment strategies (DateOffsetStrategy)
- Custom era strategies for drug exposures
- Observation period and demographic criteria
- Inclusion rules and censoring criteria
- Result limits and ordinal expressions
- Comprehensive error messages and validation warnings
- Builder pattern for SQL generation
- Pydantic models for data validation and serialization

### Documentation

- Complete README with installation instructions
- Comprehensive CLI usage documentation
- Python API examples and quick start guide
- Contributing guidelines with development setup
- Java class mapping reference for interoperability
- Package structure documentation
- Troubleshooting and FAQ sections

### Technical Details

- Built with Pydantic v2.0+ for robust validation
- Uses typing-extensions for backward compatibility
- Modular architecture matching Java CIRCE-BE structure
- Extensive test coverage across all modules
- Black, isort, flake8, and mypy for code quality
- pytest with coverage reporting

### Known Limitations

- Some advanced negative control algorithms not yet implemented
- Documentation website under development
- Performance not yet optimized for extremely large cohorts (1000+ criteria)

## [Unreleased]

### Planned

- Additional negative control generation algorithms
- Performance optimizations for large cohort definitions
- Sphinx documentation with API reference
- Additional output formats (JSON schema, XML)
- Integration examples with common OMOP tools
- Benchmarking suite against Java implementation

---

For older versions and detailed development history, see the project's Git history.

[1.0.0]: https://github.com/OHDSI/circe-be-python/releases/tag/v1.0.0
[Unreleased]: https://github.com/OHDSI/circe-be-python/compare/v1.0.0...HEAD
