# Contributing to CIRCE Python Implementation

Thank you for your interest in contributing to the CIRCE Python implementation! This document provides guidelines for contributing to the project.

## Code of Conduct

This project follows the [OHDSI Code of Conduct](https://www.ohdsi.org/web/wiki/doku.php?id=about:code_of_conduct). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of the OMOP Common Data Model
- Familiarity with the Java CIRCE-BE implementation (recommended)

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/circe-be-python.git
   cd circe-be-python
   ```

3. Install the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run tests to ensure everything is working:
   ```bash
   pytest
   ```

## Development Guidelines

### Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run these tools before committing:

```bash
black circe/
isort circe/
flake8 circe/
mypy circe/
```

### Type Hints

All functions and methods should include type hints. Use `typing` module for complex types:

```python
from typing import List, Optional, Dict, Any

def process_cohort(cohort: CohortExpression) -> Optional[str]:
    """Process a cohort expression and return SQL."""
    pass
```

### Documentation

- Use docstrings for all classes, methods, and functions
- Follow Google docstring format
- Include type information in docstrings
- Update README.md for significant changes

### Testing

- Write tests for all new functionality
- Aim for high test coverage (>80%)
- Use descriptive test names
- Group related tests in classes

Example test structure:

```python
class TestCohortExpression:
    def test_create_cohort_expression(self):
        """Test creating a basic cohort expression."""
        pass
    
    def test_cohort_expression_validation(self):
        """Test cohort expression validation."""
        pass
```

## Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them:
   ```bash
   git add .
   git commit -m "Add: brief description of changes"
   ```

3. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request on GitHub

### Pull Request Guidelines

- Provide a clear description of what the PR does
- Reference any related issues
- Ensure all tests pass
- Update documentation if needed
- Keep PRs focused and reasonably sized

### Commit Message Format

Use the following format for commit messages:

```
<type>: <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat: add CohortExpression class
fix: resolve SQL generation issue
docs: update README with examples
```

## Project Structure

The project follows the Java CIRCE-BE structure:

```
circe/
├── cohortdefinition/          # Core cohort definition classes
│   ├── builders/              # SQL query builders
│   ├── printfriendly/         # Human-readable output
│   └── negativecontrols/      # Negative controls
├── vocabulary/                # Concept management
├── check/                     # Validation framework
└── helper/                    # Utilities
```

## Implementation Guidelines

### Matching Java Implementation

- Follow the Java CIRCE-BE class structure as closely as possible
- Use the same field names (convert camelCase to snake_case)
- Maintain the same validation logic
- Ensure SQL generation produces equivalent results

### Python Best Practices

- Use Pydantic for data validation
- Follow PEP 8 style guidelines
- Use dataclasses where appropriate
- Implement proper error handling
- Use type hints throughout

## Reporting Issues

When reporting issues:

1. Check existing issues first
2. Provide a clear description
3. Include steps to reproduce
4. Provide expected vs actual behavior
5. Include environment details (Python version, OS, etc.)

## Getting Help

- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **OHDSI Community**: Join the OHDSI community for broader discussions

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a release tag
4. Publish to PyPI

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
