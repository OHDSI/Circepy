---
orphan: true
---

# Release Checklist

This checklist ensures a smooth and error-free release process for publishing to PyPI.

## Pre-Release Checklist

### Code Quality

- [ ] All tests passing: `uv run pytest`
- [ ] Code coverage meets minimum (71%+): `uv run pytest --cov`
- [ ] No linting errors: `uv run ruff check .`
- [ ] Code formatted: `uv run ruff format .`
- [ ] Pre-commit hooks pass: `uv run pre-commit run --all-files`
- [ ] No security vulnerabilities in dependencies: `pip-audit` (if installed)

### Documentation

- [ ] Version updated in `pyproject.toml`
- [ ] Version updated in `circe/__init__.py` (`__version__`)
- [ ] `CHANGELOG.md` updated with release notes
- [ ] `README.md` reviewed and up-to-date
- [ ] All example files tested and working
- [ ] Documentation links verified

### Package Structure

- [ ] `LICENSE` file present
- [ ] `MANIFEST.in` includes all necessary files
- [ ] `circe/py.typed` marker file exists
- [ ] No sensitive information in code or configs
- [ ] `.gitignore` properly excludes build artifacts

## Build Process

### 1. Clean Previous Builds

```bash
# Remove old build artifacts
rm -rf build/ dist/ *.egg-info/

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
find . -type f -name '*.pyc' -delete
```

- [ ] Build artifacts cleaned

### 2. Build the Package

```bash
# Install/upgrade build tools
pip install --upgrade build twine

# Build source distribution and wheel
python -m build
```

- [ ] Build completed successfully
- [ ] Generated files in `dist/`:
  - [ ] `ohdsi-circe-python-alpha-X.Y.Z.tar.gz` (source distribution)
  - [ ] `ohdsi-circe-python-alpha-X.Y.Z-py3-none-any.whl` (wheel)

### 3. Check Package

```bash
# Check package with twine
twine check dist/*
```

- [ ] Package check passes with no errors
- [ ] README renders correctly

## Local Testing

### 4. Test Installation Locally

```bash
# Create a test virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from wheel
pip install dist/ohdsi-circe-python-alpha-X.Y.Z-py3-none-any.whl

# Test imports
python -c "from circe import CohortExpression; print('✓ Import successful')"

# Test CLI
circe --help

# Run a quick test
python -c "from circe import __version__; print(f'Version: {__version__}')"

# Deactivate and clean up
deactivate
rm -rf test_env
```

- [ ] Package installs without errors
- [ ] Imports work correctly
- [ ] CLI command works
- [ ] Version number is correct

## Upload to TestPyPI

### 5. Upload to TestPyPI (Optional but Recommended)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# You'll need TestPyPI credentials:
# Username: __token__
# Password: your-testpypi-token
```

- [ ] Uploaded to TestPyPI successfully
- [ ] TestPyPI page loads: https://test.pypi.org/project/ohdsi-circe-python-alpha/

### 6. Test Installation from TestPyPI

```bash
# Create a new test environment
python -m venv testpypi_env
source testpypi_env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ohdsi-circe-python-alpha

# Test the installation
python -c "from circe import CohortExpression; print('✓ TestPyPI installation works')"
circe --help

# Clean up
deactivate
rm -rf testpypi_env
```

- [ ] Installation from TestPyPI works
- [ ] All functionality works as expected

## Production Release

### 7. Create Git Tag

```bash
# Create annotated tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# Push tag to remote
git push origin vX.Y.Z
```

- [ ] Git tag created
- [ ] Tag pushed to remote repository

### 8. Upload to PyPI

```bash
# Upload to production PyPI
twine upload dist/*

# You'll need PyPI credentials:
# Username: __token__
# Password: your-pypi-token
```

- [ ] Uploaded to PyPI successfully
- [ ] PyPI page loads: https://pypi.org/project/ohdsi-circe-python-alpha/

### 9. Verify Production Installation

```bash
# Create final test environment
python -m venv prod_test_env
source prod_test_env/bin/activate

# Install from PyPI
pip install ohdsi-circe-python-alpha

# Verify installation
python -c "from circe import __version__; print(f'Installed version: {__version__}')"
circe --help

# Run a complete test
cd examples
python basic_cohort.py

# Clean up
deactivate
cd ..
rm -rf prod_test_env
```

- [ ] Installation from PyPI works
- [ ] Version number is correct
- [ ] Examples run successfully

## Post-Release

### 10. Update Repository

- [ ] Create GitHub release with release notes
- [ ] Update documentation website (if applicable)
- [ ] Announce release on relevant channels:
  - [ ] GitHub Discussions
  - [ ] OHDSI Forums
  - [ ] Project mailing list

### 11. Prepare for Next Development Cycle

```bash
# Bump version for development
# Edit pyproject.toml: version = "X.Y.Z+1.dev0"
# Edit circe/__init__.py: __version__ = "X.Y.Z+1.dev0"
```

- [ ] Version bumped to next development version
- [ ] Changes committed to main branch

## Troubleshooting

### Common Issues

**Build fails with "No module named 'X'"**
- Install build dependencies: `pip install build wheel setuptools`

**Twine upload fails with authentication error**
- Ensure you're using `__token__` as username
- Generate API token at https://pypi.org/manage/account/token/

**Package description doesn't render on PyPI**
- Check `readme` field in pyproject.toml
- Run `twine check dist/*` to validate

**Import errors after installation**
- Check MANIFEST.in includes all necessary files
- Verify package structure with `tar -tzf dist/*.tar.gz`

**Tests fail on fresh install**
- Tests are not included in distribution (by design)
- Test locally before building package

## Credentials Setup

### PyPI API Token

1. Create account at https://pypi.org/
2. Go to Account Settings → API tokens
3. Generate token with scope for "ohdsi-circe-python-alpha" project
4. Store securely (use `keyring` or `.pypirc`)

### TestPyPI API Token

1. Create account at https://test.pypi.org/
2. Generate separate token for testing
3. Configure in `~/.pypirc`:

```ini
[testpypi]
  repository = https://test.pypi.org/legacy/
  username = __token__
  password = pypi-AgEIcHlw... (your token)
```

## Emergency Rollback

If a critical issue is discovered after release:

1. **Yank the release** (doesn't delete, but prevents new installs):
   ```bash
   # On PyPI website, go to release and click "Delete release"
   # Or use API
   ```

2. **Fix the issue** in code

3. **Bump version** (e.g., X.Y.Z → X.Y.Z+1)

4. **Follow full release process** again

## Notes

- **Never force push** to main after tagging
- **Never delete published releases** from PyPI (yank instead)
- **Always test on TestPyPI** first for major releases
- **Keep credentials secure** and rotate regularly
- **Document any manual steps** needed for release
