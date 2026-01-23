# Package Name Update Summary

## 🎯 New Package Name: `ohdsi-circe-python-alpha`

The PyPI package name has been changed from `ohdsi-circe` to **`ohdsi-circe-python-alpha`** because `ohdsi-circe` is already taken on PyPI by an R/Java wrapper package.

## ✅ What Changed

### Package Metadata
- **PyPI package name**: `ohdsi-circe` → **`ohdsi-circe-python-alpha`**
- **Module name**: `circe` (unchanged - users still do `import circe`)
- **Repository**: Now under OHDSI organization at `https://github.com/OHDSI/Circepy`

### Installation Commands

**Old:**
```bash
pip install ohdsi-circe  # Not available (name taken)
```

**New:**
```bash
pip install ohdsi-circe-python-alpha
```

**Import stays the same:**
```python
import circe
from circe import CohortExpression
```

## 📝 Updated Files

The following files have been automatically updated with the new package name:

### Core Configuration
- ✅ `pyproject.toml` - Package name and URLs
- ✅ `.github/workflows/publish-pypi.yml` - PyPI publishing workflow
- ✅ `.github/workflows/release.yml` - Release workflow

### Documentation
- ✅ `README.md` - All references and installation instructions
- ✅ `INSTALLATION.md` - Installation guide
- ✅ `CONTRIBUTING.md` - Contributing guidelines
- ✅ `PUBLISHING_GUIDE.md` - Publishing instructions
- ✅ `QUICK_START_PUBLISHING.md` - Quick start guide
- ✅ `RELEASE_CHECKLIST.md` - Release checklist
- ✅ `docs/README.md` - Documentation readme
- ✅ `docs/CONTRIBUTING.md` - Docs contributing guide
- ✅ `docs/RELEASE_CHECKLIST.md` - Docs release checklist
- ✅ `examples/README.md` - Examples readme

## 🔗 New URLs

### PyPI
- **Package**: https://pypi.org/project/ohdsi-circe-python-alpha/
- **TestPyPI**: https://test.pypi.org/project/ohdsi-circe-python-alpha/

### ReadTheDocs
- **Documentation**: https://ohdsi-circe-python-alpha.readthedocs.io/
- **Latest**: https://ohdsi-circe-python-alpha.readthedocs.io/en/latest/
- **Stable**: https://ohdsi-circe-python-alpha.readthedocs.io/en/stable/

### GitHub
- **Repository**: https://github.com/OHDSI/Circepy
- **Issues**: https://github.com/OHDSI/Circepy/issues

## 📦 PyPI Package Details

```toml
[project]
name = "ohdsi-circe-python-alpha"
version = "0.1.0"
description = "Python implementation of OHDSI CIRCE-BE for cohort definition and SQL generation"
```

**Package name**: `ohdsi-circe-python-alpha`  
**Module name**: `circe`  
**Command**: `circe` (CLI tool)

## 🚀 Publishing Checklist Updates

When setting up PyPI/ReadTheDocs, use these new values:

### PyPI Setup
- **Package name**: `ohdsi-circe-python-alpha` (not `ohdsi-circe`)
- **Token scope**: After first upload, scope to `ohdsi-circe-python-alpha` project

### ReadTheDocs Setup
- **Project name**: `ohdsi-circe-python-alpha`
- **Project slug**: `ohdsi-circe-python-alpha`
- **Documentation URL**: `https://ohdsi-circe-python-alpha.readthedocs.io/`

### GitHub Secrets
- **Secret name**: `PYPI_API_TOKEN`
- **Token scope**: `ohdsi-circe-python-alpha` project on PyPI

### Trusted Publisher Setup (Alternative to API Token)
If using PyPI Trusted Publishers:
- **PyPI Project**: `ohdsi-circe-python-alpha`
- **GitHub Owner**: `OHDSI`
- **Repository**: `Circepy`
- **Workflow**: `publish-pypi.yml`

## 🎯 Next Steps

1. **Verify the changes** by building locally:
   ```bash
   python -m build
   # Should create: dist/ohdsi-circe-python-alpha-0.1.0-py3-none-any.whl
   ```

2. **Create PyPI account** at https://pypi.org/account/register/

3. **Set up GitHub secrets** with your PyPI token

4. **Import to ReadTheDocs** using project name `ohdsi-circe-python-alpha`

5. **Test publish to TestPyPI** (optional):
   ```bash
   twine upload --repository testpypi dist/*
   pip install --index-url https://test.pypi.org/simple/ ohdsi-circe-python-alpha
   ```

6. **Publish to production PyPI**:
   ```bash
   twine upload dist/*
   # Or push a git tag to trigger automated publishing
   ```

## ❓ FAQ

**Q: Why `ohdsi-circe-python-alpha` instead of `ohdsi-circe`?**  
A: The name `ohdsi-circe` is already taken on PyPI by another package (an R/Java wrapper).

**Q: Will this affect existing code?**  
A: No. The module name is still `circe`, so all `import circe` statements work unchanged.

**Q: What about the other package with the same name?**  
A: The existing `ohdsi-circe` package is a wrapper to R/Java CIRCE. This `ohdsi-circe-python-alpha` package is a pure Python implementation. They serve different purposes.

**Q: Can I still use `ohdsi-circe` locally?**  
A: No, the package name in `pyproject.toml` has been changed to `ohdsi-circe-python-alpha`. All future distributions will use this name.

**Q: Does the CLI command change?**  
A: No, the CLI command is still `circe`.

## 📋 Verification Commands

After changes, verify everything still works:

```bash
# Check pyproject.toml
grep 'name = "ohdsi-circe-python-alpha"' pyproject.toml

# Build package
python -m build

# Check distribution name
ls dist/
# Should show: ohdsi-circe-python-alpha-0.1.0-py3-none-any.whl and ohdsi-circe-python-alpha-0.1.0.tar.gz

# Test installation locally
pip install dist/*.whl
python -c "import circe; print(circe.__version__)"
circe --help

# Uninstall
pip uninstall ohdsi-circe-python-alpha
```

## ✅ All Set!

The package is now ready to be published to PyPI as **`ohdsi-circe-python-alpha`**.

Follow the guides:
- 📘 [PUBLISHING_GUIDE.md](PUBLISHING_GUIDE.md) - Complete publishing guide
- 🚀 [QUICK_START_PUBLISHING.md](QUICK_START_PUBLISHING.md) - Quick start for publishing
