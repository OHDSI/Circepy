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

> [!NOTE]
> This is a private development repository. Ensure you have access before attempting to clone.

1. Clone the repository
   ```bash
   git clone https://github.com/OHDSI/Circepy.git
   cd Circepy
   ```

2. Install the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests to ensure everything is working:
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

Releases are managed by maintainers following a structured process to ensure quality and consistency.

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.0.0)
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Steps

1. **Prepare the Release**
   - Update version in `pyproject.toml`
   - Update version in `circe/__init__.py`
   - Update `CHANGELOG.md` with release notes
   - Ensure all tests pass: `pytest`
   - Verify coverage is adequate: `pytest --cov`

2. **Build the Package**
   ```bash
   # Clean previous builds
   rm -rf build/ dist/ *.egg-info/
   
   # Build package
   python -m build
   
   # Check package
   twine check dist/*
   ```

3. **Test on TestPyPI** (Optional but recommended)
   ```bash
   # Upload to TestPyPI
   twine upload --repository testpypi dist/*
   
   # Test installation
   pip install --index-url https://test.pypi.org/simple/ ohdsi-circepy
   ```

4. **Create Git Tag**
   ```bash
   git tag -a vX.Y.Z -m "Release version X.Y.Z"
   git push origin vX.Y.Z
   ```

5. **Publish to PyPI**
   ```bash
   twine upload dist/*
   ```

6. **Post-Release Tasks**
   - Create GitHub release with release notes
   - Announce release in community channels
   - Update documentation if needed

### Detailed Release Checklist

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for a comprehensive checklist covering:
- Pre-release quality checks
- Build and test procedures
- TestPyPI validation
- Production release steps
- Post-release tasks
- Troubleshooting common issues

### Release Permissions

Only maintainers with PyPI publishing rights can make releases. If you believe a release is needed:

1. Open an issue describing the changes
2. Tag maintainers with `@maintainer`
3. Provide summary of changes for release notes

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
