# Installation Guide

> [!CAUTION]
> **This project is currently under active development and testing.** It is a Python implementation of the Java [OHDSI CIRCE-BE](https://github.com/OHDSI/circe-be) library. This is an Alpha release and should be used with caution in production environments.

## Prerequisites

- **Python 3.8 or higher** (Python 3.9+ recommended)
- **Git** for cloning the repository
- **pip** package manager (usually included with Python)

## Installation from Source (Current Method)

Since this package is currently in private development, you'll need to install it directly from the GitHub repository.

### Step 1: Clone the Repository

```bash
git clone https://github.com/azimov/circepy.git
cd circepy
```

### Step 2: Install in Development Mode

For development and testing, install the package in editable mode with all development dependencies:

```bash
pip install -e ".[dev]"
```

This will install:
- The `circe` package in editable mode (changes to source code are immediately available)
- All development tools (pytest, black, mypy, etc.)
- Optional dependencies for documentation and testing

### Step 3: Verify Installation

Test that the installation was successful:

```bash
# Check the CLI is available
circe --help

# Verify the version
python -c "from circe import __version__; print(f'CIRCE Python version: {__version__}')"

# Run a quick test
pytest tests/ -v --maxfail=5
```

## Installation for Usage Only

If you only want to use the package without development tools:

```bash
pip install -e .
```

This installs only the core dependencies (`pydantic` and `typing-extensions`).

## PyPI Installation (Coming Soon)

> [!NOTE]
> **PyPI package is not yet available.** Once the package reaches stable release, it will be published to PyPI and you'll be able to install it with:
> 
> ```bash
> # This will work in future releases
> pip install ohdsi-circe
> ```

## Installation Options

### Virtual Environment (Recommended)

It's recommended to use a virtual environment to avoid dependency conflicts:

```bash
# Create virtual environment
python -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate

# Install the package
pip install -e ".[dev]"
```

### Install Specific Extras

The package provides several optional dependency groups:

```bash
# Development tools only
pip install -e ".[dev]"

# Documentation tools
pip install -e ".[docs]"

# All extras
pip install -e ".[dev,docs]"
```

## Verifying Your Installation

### Check Installed Version

```bash
circe --version
```

### Run Example Scripts

Navigate to the examples directory and run sample scripts:

```bash
cd examples
python basic_cohort.py
python validate_cohort.py
```

### Run the Test Suite

Ensure your installation is working correctly:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=circe --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Troubleshooting

### Import Errors

**Problem**: `ImportError: No module named 'circe'`

**Solution**: Ensure you installed in editable mode from the repository root:
```bash
cd circepy
pip install -e .
```

### CLI Not Found

**Problem**: `circe: command not found`

**Solution**: Ensure your Python scripts directory is in your PATH, or use:
```bash
python -m circe --help
```

### Version Mismatch

**Problem**: `circe --version` shows an old version

**Solution**: Reinstall the package:
```bash
pip uninstall ohdsi-circe circe
cd circepy
pip install -e ".[dev]"
```

### Permission Errors

**Problem**: Permission denied during installation

**Solution**: Use a virtual environment (recommended) or install with `--user` flag:
```bash
pip install -e . --user
```

### Pydantic Validation Errors

**Problem**: Errors about Pydantic models or validation

**Solution**: Ensure you have Pydantic v2.0+:
```bash
pip install --upgrade pydantic>=2.0.0
```

## Updating Your Installation

To get the latest changes from the repository:

```bash
cd circepy
git pull origin main  # or git pull origin develop for latest development
pip install -e ".[dev]"  # Reinstall if dependencies changed
```

## Uninstalling

To remove the package:

```bash
pip uninstall ohdsi-circe
```

## System Requirements

### Minimum Requirements
- Python 3.8+
- 100 MB free disk space
- 512 MB RAM

### Recommended Requirements
- Python 3.11+
- 500 MB free disk space (for development)
- 2 GB RAM (for running full test suite)

## Getting Help

If you encounter installation issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the [Contributing Guide](CONTRIBUTING.md)
3. Open an issue on [GitHub Issues](https://github.com/azimov/circepy/issues)
4. Check existing issues for similar problems

## Next Steps

After successful installation:

1. Read the [README.md](README.md) for an overview
2. Explore the [examples/](examples/) directory
3. Review the [CONTRIBUTING.md](CONTRIBUTING.md) if you want to contribute
4. Check the [CHANGELOG.md](CHANGELOG.md) for recent updates
