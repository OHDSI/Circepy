# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.0] - 2026-01-23

### Added

- Initial Alpha Release of the CIRCE Python implementation.
- Full parity with OHDSI CIRCE-BE Java library for cohort definition and SQL generation.
- Expanded test suite with 3,400+ tests including parity checks.
- Comprehensive documentation and GitHub Actions release workflows.

## [Unreleased]

### Planned
- Performance optimizations for large cohort definitions
- Additional output formats (JSON schema, XML)
- Integration examples with common OMOP tools
---

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

- Negative control cohort classes yet implemented
- Documentation website under development
- Performance not yet optimized for extremely large cohorts (1000+ criteria)