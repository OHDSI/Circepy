# Publishing Guide for OHDSI Circepy

This guide covers how to publish the Circepy package to PyPI and set up documentation on ReadTheDocs.

## 📦 Publishing to PyPI

### Prerequisites

Before you can publish to PyPI, you need:

1. **PyPI Account**: Create an account at [https://pypi.org/account/register/](https://pypi.org/account/register/)
2. **API Token**: Generate an API token for secure authentication
3. **TestPyPI Account** (optional but recommended): Create an account at [https://test.pypi.org/](https://test.pypi.org/)

### Step 1: Set Up PyPI API Token

1. Log in to [PyPI](https://pypi.org/)
2. Go to **Account Settings** → **API tokens**
3. Click **Add API token**
4. Give it a name (e.g., "Circepy Publishing")
5. **Scope**: Start with "Entire account" (you can narrow it later to just this project)
6. Copy the token (starts with `pypi-...`) - **you'll only see it once!**

Store your token securely using one of these methods:

#### Option A: Using GitHub Secrets (Recommended for CI/CD)

1. Go to your GitHub repository: `https://github.com/OHDSI/Circepy`
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `PYPI_API_TOKEN`
5. Value: Your PyPI token (the full `pypi-...` string)

#### Option B: Using `.pypirc` (For Local Publishing)

Create or edit `~/.pypirc`:

```ini
[pypi]
  username = __token__
  password = pypi-AgEIcHlw... (your actual token here)

[testpypi]
  repository = https://test.pypi.org/legacy/
  username = __token__
  password = pypi-AgEIcHlw... (your TestPyPI token here)
```

Set permissions:
```bash
chmod 600 ~/.pypirc
```

### Step 2: Prepare for Release

Follow the detailed checklist in [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md). Key steps:

1. **Update version number** in:
   - `pyproject.toml` (line 7)
   - `circe/__init__.py` (`__version__`)
   
2. **Update CHANGELOG.md** with release notes

3. **Run all tests**:
   ```bash
   uv run pytest
   uv run pytest --cov
   ```

4. **Format and lint**:
   ```bash
   uv run ruff check .
   uv run ruff format .
   uv run pre-commit run --all-files
   ```

5. **Clean old builds**:
   ```bash
   rm -rf build/ dist/ *.egg-info/
   ```

### Step 3: Build the Package

```bash
# Install build tools
pip install --upgrade build twine

# Build package
python -m build
```

This creates:
- `dist/ohdsi-circe-python-alpha-X.Y.Z.tar.gz` (source distribution)
- `dist/ohdsi-circe-python-alpha-X.Y.Z-py3-none-any.whl` (wheel)

### Step 4: Test the Build

```bash
# Check package validity
twine check dist/*

# Test installation locally
python -m venv test_env
source test_env/bin/activate
pip install dist/*.whl
python -c "from circe import __version__; print(__version__)"
circe --help
deactivate
rm -rf test_env
```

### Step 5: Upload to TestPyPI (Recommended First)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*
```

Test the installation:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ohdsi-circe-python-alpha
```

### Step 6: Upload to Production PyPI

When ready for production:

```bash
# Upload to PyPI
twine upload dist/*
```

Or use the token directly:
```bash
twine upload --username __token__ --password pypi-YOUR_TOKEN_HERE dist/*
```

### Step 7: Create GitHub Release

```bash
# Tag the release
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

The GitHub Actions workflow in `.github/workflows/release.yml` will automatically:
- Build the package
- Create a GitHub release
- Attach distribution files

**Note**: The workflow doesn't auto-publish to PyPI yet. To enable that, update `.github/workflows/release.yml` to add:

```yaml
- name: Publish to PyPI
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
  run: |
    twine upload dist/*
```

---

## 📚 Publishing to ReadTheDocs

Your documentation is already configured! You just need to set it up on ReadTheDocs.

### Step 1: Import Project on ReadTheDocs

1. Go to [https://readthedocs.org/](https://readthedocs.org/)
2. **Sign up / Log in** with your GitHub account
3. Click **Import a Project**
4. Select **OHDSI/Circepy** from your repositories
5. Click **Next**

### Step 2: Configure Project Settings

ReadTheDocs will automatically detect your `.readthedocs.yaml` configuration file.

#### Basic Settings
- **Name**: `ohdsi-circe-python-alpha` (or your preferred name)
- **Repository URL**: `https://github.com/OHDSI/Circepy`
- **Default branch**: `main`
- **Default version**: `latest`

#### Advanced Settings (Optional)
- Go to **Admin** → **Advanced Settings**
- **Default branch**: `main`
- **Documentation type**: `Sphinx Html`
- **Requirements file**: `requirements.txt`
- **Python interpreter**: `CPython 3.11`

### Step 3: Build Documentation

ReadTheDocs will automatically:
1. Build docs on every push to `main` or `develop`
2. Create versioned docs for each git tag
3. Host at `https://ohdsi-circe-python-alpha.readthedocs.io/`

To manually trigger a build:
- Go to your ReadTheDocs project dashboard
- Click **Versions**
- Click **Build** next to the version you want to build

### Step 4: Configure Webhooks (Automatic)

ReadTheDocs automatically creates a webhook in your GitHub repository to trigger builds on commits.

You can verify this:
1. Go to your GitHub repository
2. **Settings** → **Webhooks**
3. You should see a webhook for `https://readthedocs.org/api/v2/webhook/...`

### Step 5: Enable Versioning

For versioned documentation:

1. Go to **Versions** in your ReadTheDocs dashboard
2. **Activate** the versions you want (e.g., `latest`, `stable`, specific tags)
3. Set **stable** to point to your latest release tag

### Step 6: Custom Domain (Optional)

If you want a custom domain like `docs.ohdsi.org/ohdsi-circe-python-alpha`:

1. Go to **Admin** → **Domains**
2. Add your custom domain
3. Update your DNS records as instructed

---

## 🔄 Automated Publishing Workflow

### Current Setup

Your `.github/workflows/release.yml` is configured to:
- ✅ Build package on git tags (`v*.*.*`)
- ✅ Run verification tests
- ✅ Create GitHub releases
- ✅ Upload artifacts

### To Enable Auto-Publishing to PyPI

Add this job to `.github/workflows/release.yml` (after the build job):

```yaml
  publish:
    needs: build-and-release
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # IMPORTANT: for trusted publishing
    
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: python-package-distributions
          path: dist/
      
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

### Trusted Publishing (Recommended Alternative)

PyPI supports "Trusted Publishers" which eliminates the need for API tokens:

1. Go to [PyPI Project Settings](https://pypi.org/manage/project/ohdsi-circe-python-alpha/)
2. Navigate to **Publishing** → **Add a new pending publisher**
3. Add:
   - **PyPI Project Name**: `ohdsi-circe-python-alpha`
   - **Owner**: `OHDSI`
   - **Repository**: `Circepy`
   - **Workflow name**: `release.yml`
   - **Environment**: (leave blank or use `release`)

Then update the workflow to use trusted publishing:

```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  # No password needed with trusted publishing!
```

---

## 🎯 Quick Release Checklist

- [ ] Update version in `pyproject.toml` and `circe/__init__.py`
- [ ] Update `CHANGELOG.md`
- [ ] Run tests: `uv run pytest --cov`
- [ ] Clean build: `rm -rf dist/ build/`
- [ ] Build package: `python -m build`
- [ ] Check package: `twine check dist/*`
- [ ] Upload to TestPyPI (optional): `twine upload --repository testpypi dist/*`
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Create and push git tag: `git tag -a v0.1.0 -m "Release 0.1.0" && git push origin v0.1.0`
- [ ] Verify GitHub release was created
- [ ] Verify PyPI package: `pip install ohdsi-circe-python-alpha`
- [ ] Verify ReadTheDocs build succeeded

---

## 📞 Support

- **PyPI Issues**: https://github.com/pypi/support
- **ReadTheDocs Issues**: https://github.com/readthedocs/readthedocs.org/issues
- **Circepy Issues**: https://github.com/OHDSI/Circepy/issues

---

## 📖 Additional Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [ReadTheDocs Documentation](https://docs.readthedocs.io/)
- [PyPI Help](https://pypi.org/help/)
- [Semantic Versioning](https://semver.org/)
