# Installation Guide

> [!CAUTION]
> **This project is currently under active development and testing.** It is a Python implementation of the Java [OHDSI CIRCE-BE](https://github.com/OHDSI/circe-be) library. This is an Alpha release and should be used with caution in production environments.

## Prerequisites

- **Python 3.9 or higher** (Python 3.9+ recommended)
- **Git** for cloning the repository
- **uv** for the recommended, lockfile-backed workflow
- **pip** package manager for fallback installation paths

## Installation from Source (Current Method)

Since this package is currently in private development, you'll need to install it directly from the GitHub repository.
The recommended workflow uses `uv` and the checked-in `uv.lock` for a reproducible environment.

### Step 1: Clone the Repository

```bash
git clone https://github.com/OHDSI/Circepy.git
cd Circepy
```

### Step 2: Install with uv

For development and testing, sync the project environment with the locked dependency set:

```bash
uv sync --extra dev

# Install Git hooks
uv run pre-commit install
```

This will install:
- The `circe` package in editable mode
- The locked development toolchain (pytest, Ruff, pre-commit, etc.)
- A project-local virtual environment managed by `uv`

### Step 3: Verify Installation

Test that the installation was successful:

```bash
# Check the CLI is available
uv run circe --help

# Verify the version
uv run python -c "from circe import __version__; print(f'CIRCE Python version: {__version__}')"

# Run a quick test
uv run pytest tests/ -v --maxfail=5
```

## Installation for Usage Only

If you only want to use the package without development tools:

```bash
uv sync
```

This installs the project with its core dependencies into the `uv`-managed environment.

## PyPI Installation

> [!NOTE]
> The currently published alpha package is available as `ohdsi-circe-python-alpha`.
> The long-term package name is expected to become `ohdsi-circepy` once that package name is available for takeover.
> 
> ```bash
> # Current alpha package
> pip install ohdsi-circe-python-alpha
>
> # Planned future package name
> pip install ohdsi-circepy
> ```

## Installation Options

### uv Extras

The project defines optional dependency groups that can be synced into the `uv` environment:

```bash
# Core package only
uv sync

# Development tools
uv sync --extra dev

# Documentation tools
uv sync --extra docs

# Development and documentation tools
uv sync --extra dev --extra docs
```

### pip Fallback (Optional)

If you are not using `uv`, use a virtual environment and install with `pip`. This path is supported, but the `uv` workflow above is the reproducible, maintainer-tested setup.

```bash
# Create a virtual environment
python -m venv .venv

# Activate on macOS/Linux
source .venv/bin/activate

# Activate on Windows
.venv\Scripts\activate

# Install the package with development tools
pip install -e ".[dev]"
```

You can also install specific extras with `pip`:

```bash
# Documentation tools only
pip install -e ".[docs]"

# Development and documentation tools
pip install -e ".[dev,docs]"
```

## Verifying Your Installation

### Check Installed Version

```bash
uv run circe --version
```

### Run Example Scripts

Navigate to the examples directory and run sample scripts:

```bash
cd examples
uv run python basic_cohort.py
uv run python validate_cohort.py
```

### Run the Test Suite

Ensure your installation is working correctly:

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=circe --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Troubleshooting

### Import Errors

**Problem**: `ImportError: No module named 'circe'`

**Solution**: Re-sync the environment from the repository root:
```bash
cd Circepy
uv sync --extra dev
```

### CLI Not Found

**Problem**: `circe: command not found`

**Solution**: Ensure your Python scripts directory is in your PATH, or use:
```bash
uv run python -m circe --help
```

### Version Mismatch

**Problem**: `circe --version` shows an old version

**Solution**: Reinstall the package:
```bash
cd Circepy
uv sync --extra dev
```

### Permission Errors

**Problem**: Permission denied during installation

**Solution**: Prefer the `uv` workflow, which manages a project-local environment. If you are using `pip`, use a virtual environment instead of `--user`:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
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
cd Circepy
git pull origin main  # or git pull origin develop for latest development
uv sync --extra dev
```

## Uninstalling

If you are using `uv`, remove the project environment:

```bash
rm -rf .venv
```

If you installed with `pip`, remove the package with:

```bash
pip uninstall ohdsi-circe-python-alpha
```

## System Requirements

### Minimum Requirements
- Python 3.9+
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
3. Open an issue on [GitHub Issues](https://github.com/OHDSI/Circepy/issues)
4. Check existing issues for similar problems

## Next Steps

After successful installation:

1. Read the [README.md](README.md) for an overview
2. Explore the [examples/](examples/) directory
3. Review the [CONTRIBUTING.md](CONTRIBUTING.md) if you want to contribute
4. Check the [CHANGELOG.md](CHANGELOG.md) for recent updates
