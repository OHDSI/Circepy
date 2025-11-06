# CIRCE Python Implementation

A Python implementation of the OHDSI CIRCE-BE (Cohort Inclusion and Restriction Criteria Engine) for generating SQL queries from cohort definitions in the OMOP Common Data Model.

## Overview

CIRCE Python provides a comprehensive toolkit for:

- **Cohort Definition Modeling**: Create and validate cohort expressions using Python classes
- **SQL Generation**: Generate SQL queries from cohort definitions for OMOP CDM v5.0-v5.3
- **Concept Set Management**: Handle concepts and concept sets from OMOP vocabularies
- **Validation & Checking**: Comprehensive validation of cohort definitions
- **Print-Friendly Output**: Generate human-readable descriptions of cohort definitions
- **Negative Controls**: Generate negative control cohorts for validation

## ⚠️ CRITICAL: Java Fidelity Requirement

**This project MUST maintain 1:1 compatibility with Java CIRCE-BE.**

- All Python classes must exactly replicate Java functionality
- All changes must be validated against Java schema
- All field names must support both Java (camelCase) and Python (snake_case) formats
- See [JAVA_CLASS_MAPPINGS.md](JAVA_CLASS_MAPPINGS.md) for complete class mappings

**Any deviation from Java implementation is considered a breaking change.**

## Installation

```bash
pip install circe
```

## Quick Start

### Command-Line Interface

The easiest way to use CIRCE is through the command-line interface:

```bash
# Validate a cohort expression JSON file
circe validate cohort.json

# Generate SQL from a cohort expression
circe generate-sql cohort.json --output cohort.sql

# Render a cohort expression to markdown
circe render-markdown cohort.json --output cohort.md

# Process a cohort expression (validate, generate SQL, and render markdown)
circe process cohort.json --validate --sql --markdown
```

See the [CLI Documentation](#command-line-interface) section below for more details.

### Python API

```python
from circe import CohortExpression, Concept, ConceptSet

# Create a simple cohort expression
cohort = CohortExpression(
    title="Type 2 Diabetes Cohort",
    primary_criteria=PrimaryCriteria(
        criteria_list=[
            ConditionOccurrence(
                codeset_id=1,
                occurrence_start_date=DateRange(op="gte", value="2000-01-01")
            )
        ]
    ),
    concept_sets=[
        ConceptSet(
            id=1,
            name="Type 2 Diabetes",
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(concept_id=440358, concept_name="Type 2 diabetes mellitus"),
                        include_descendants=True
                    )
                ]
            )
        )
    ]
)

# Generate SQL
sql = cohort.to_sql()
print(sql)
```

## Package Structure

```
circe/
├── cohortdefinition/          # Core cohort definition classes
│   ├── builders/              # SQL query builders
│   ├── printfriendly/         # Human-readable output generation
│   └── negativecontrols/      # Negative control generation
├── vocabulary/                # Concept and concept set management
├── check/                     # Validation and checking
│   ├── checkers/              # Specific checker implementations
│   ├── operations/            # Check operations
│   ├── utils/                 # Check utilities
│   └── warnings/              # Warning classes
└── helper/                    # Utility helper classes
```

## Features

### ✅ Implemented
- [x] Package structure and setup
- [x] Basic project configuration
- [x] Test framework setup
- [x] CLI interface

### 🚧 In Progress
- [ ] Core cohort definition classes
- [ ] SQL query generation
- [ ] Concept set management
- [ ] Validation framework

### 📋 Planned
- [ ] Print-friendly output generation
- [ ] Negative controls
- [ ] Comprehensive test suite
- [ ] Documentation

## Command-Line Interface

CIRCE provides a comprehensive command-line interface for validating, generating SQL, and rendering cohort expressions.

### Validate Command

Validate a cohort expression JSON file against the CIRCE standard:

```bash
circe validate cohort.json
```

Options:
- `--verbose, -v`: Display all validation warnings including INFO level
- `--quiet, -q`: Suppress non-error output

Exit codes:
- `0`: Valid (no errors or warnings)
- `1`: Invalid (errors found)
- `2`: Valid but has warnings

### Generate SQL Command

Generate SQL from a cohort expression:

```bash
# Output to stdout
circe generate-sql cohort.json

# Output to file
circe generate-sql cohort.json --output cohort.sql

# With custom schema names
circe generate-sql cohort.json --cdm-schema my_cdm --vocab-schema my_vocab --cohort-id 123
```

Options:
- `--output, -o`: Output SQL file path (default: stdout)
- `--sql-options`: JSON file with BuildExpressionQueryOptions
- `--cdm-schema`: CDM schema name (default: `@cdm_database_schema`)
- `--vocab-schema`: Vocabulary schema name (default: `@vocabulary_database_schema`)
- `--cohort-id`: Cohort ID for SQL generation
- `--validate`: Validate before generating SQL (default: True)
- `--no-validate`: Skip validation before generating SQL
- `--verbose, -v`: Verbose output
- `--quiet, -q`: Suppress non-error output

### Render Markdown Command

Render a cohort expression to human-readable markdown:

```bash
# Output to stdout
circe render-markdown cohort.json

# Output to file
circe render-markdown cohort.json --output cohort.md
```

Options:
- `--output, -o`: Output markdown file path (default: stdout)
- `--validate`: Validate before rendering markdown (default: True)
- `--no-validate`: Skip validation before rendering markdown
- `--verbose, -v`: Verbose output
- `--quiet, -q`: Suppress non-error output

### Process Command

Process a cohort expression with multiple operations:

```bash
# Validate, generate SQL, and render markdown
circe process cohort.json --validate --sql --markdown

# Generate SQL with custom output file
circe process cohort.json --sql output.sql

# Generate SQL and markdown with default file names
circe process cohort.json --sql --markdown
```

Options:
- `--validate`: Validate the cohort expression
- `--sql [FILE]`: Generate SQL (optionally specify output file, default: input file with .sql extension)
- `--markdown [FILE]`: Render markdown (optionally specify output file, default: input file with .md extension)
- `--sql-options`: JSON file with BuildExpressionQueryOptions
- `--cdm-schema`: CDM schema name (default: `@cdm_database_schema`)
- `--vocab-schema`: Vocabulary schema name (default: `@vocabulary_database_schema`)
- `--cohort-id`: Cohort ID for SQL generation
- `--verbose, -v`: Verbose output
- `--quiet, -q`: Suppress non-error output

### Examples

```bash
# Validate a cohort expression
circe validate my_cohort.json

# Generate SQL with custom schema
circe generate-sql my_cohort.json --output my_cohort.sql \
    --cdm-schema my_cdm_schema \
    --vocab-schema my_vocab_schema \
    --cohort-id 1

# Generate SQL and markdown in one command
circe process my_cohort.json --sql --markdown

# Validate, generate SQL, and render markdown
circe process my_cohort.json --validate --sql my_cohort.sql --markdown my_cohort.md
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/OHDSI/circe-be-python.git
cd circe-be-python
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black circe/
isort circe/
```

### Type Checking

```bash
mypy circe/
```

## Contributing

Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project is based on the Java CIRCE-BE implementation by the OHDSI community. We thank all contributors to the original Java implementation.

## Support

- **Documentation**: [https://circe-be-python.readthedocs.io/](https://circe-be-python.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/OHDSI/circe-be-python/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OHDSI/circe-be-python/discussions)

## Related Projects

- [OHDSI CIRCE-BE (Java)](https://github.com/OHDSI/circe-be) - Original Java implementation
- [OHDSI Common Data Model](https://github.com/OHDSI/CommonDataModel) - OMOP CDM specification
- [OHDSI Atlas](https://github.com/OHDSI/Atlas) - Web-based cohort definition tool