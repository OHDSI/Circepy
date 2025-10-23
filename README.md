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

## Installation

```bash
pip install circe
```

## Quick Start

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
- [ ] CLI interface

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