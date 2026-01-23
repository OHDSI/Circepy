# Quick Start: Publishing Circepy

## 🚀 For Your First Release (v0.1.0)

### 1️⃣ Set Up PyPI Account (One-time)

```bash
# 1. Create PyPI account at https://pypi.org/account/register/
# 2. Enable 2FA (required for publishing)
# 3. Create API token:
#    - Go to https://pypi.org/manage/account/token/
#    - Click "Add API token"
#    - Name: "Circepy Publishing"
#    - Scope: "Entire account" (or specific to ohdsi-circe-python-alpha after first upload)
#    - Copy the token (starts with pypi-...)
```

### 2️⃣ Store Your Token

**For GitHub Actions (Automated):**
```bash
# On GitHub:
# Settings → Secrets and variables → Actions → New repository secret
# Name: PYPI_API_TOKEN
# Value: <your-pypi-token>
```

**For Manual Publishing:**
```bash
# Create ~/.pypirc
cat > ~/.pypirc << 'EOF'
[pypi]
  username = __token__
  password = pypi-YOUR_ACTUAL_TOKEN_HERE

[testpypi]
  repository = https://test.pypi.org/legacy/
  username = __token__
  password = pypi-YOUR_TESTPYPI_TOKEN_HERE
EOF

chmod 600 ~/.pypirc
```

### 3️⃣ Manual Release Steps

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build package
pip install --upgrade build twine
python -m build

# Check package
twine check dist/*

# Test locally
python -m venv test_env
source test_env/bin/activate
pip install dist/*.whl
python -c "from circe import __version__; print(__version__)"
circe --help
deactivate && rm -rf test_env

# Upload to TestPyPI (optional)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*

# Create git tag
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

### 4️⃣ Automated Release (Recommended)

```bash
# 1. Update version in:
#    - pyproject.toml (line 7)
#    - circe/__init__.py (line 22)

# 2. Update CHANGELOG.md

# 3. Commit and push
git add .
git commit -m "Bump version to 0.1.0"
git push origin main

# 4. Create and push tag
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0

# 5. GitHub Actions will automatically:
#    - Build the package
#    - Create GitHub release
#    - Run the publish-pypi.yml workflow (if configured)
```

---

## 📚 ReadTheDocs Setup (One-time)

### 1️⃣ Import Project

1. Go to [https://readthedocs.org/](https://readthedocs.org/)
2. Sign in with GitHub
3. Click **Import a Project**
4. Select **OHDSI/Circepy**
5. Click **Next**

### 2️⃣ Configure (Auto-detected from `.readthedocs.yaml`)

- **Name**: `ohdsi-circe-python-alpha`
- **Repository URL**: `https://github.com/OHDSI/Circepy`
- **Default branch**: `main`

Click **Finish** - that's it!

### 3️⃣ Access Documentation

Your docs will be available at:
- **Latest**: https://ohdsi-circe-python-alpha.readthedocs.io/en/latest/
- **Stable**: https://ohdsi-circe-python-alpha.readthedocs.io/en/stable/
- **Specific version**: https://ohdsi-circe-python-alpha.readthedocs.io/en/v0.1.0/

ReadTheDocs automatically builds on:
- Every push to `main` or `develop`
- Every new git tag

---

## 🔄 For Future Releases

```bash
# 1. Update version numbers
vim pyproject.toml circe/__init__.py

# 2. Update CHANGELOG.md

# 3. Commit, tag, push
git add .
git commit -m "Bump version to X.Y.Z"
git push origin main
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z

# Done! GitHub Actions handles the rest.
```

---

## ✅ Verify Your Release

After publishing:

```bash
# Install from PyPI
pip install ohdsi-circe-python-alpha

# Verify version
python -c "from circe import __version__; print(__version__)"

# Check on PyPI
open https://pypi.org/project/ohdsi-circe-python-alpha/

# Check documentation
open https://ohdsi-circe-python-alpha.readthedocs.io/
```

---

## 🆘 Troubleshooting

**"Invalid credentials" when uploading:**
- Ensure you're using `__token__` as username (exactly, including underscores)
- Password should start with `pypi-`

**"Package already exists" error:**
- You can't re-upload the same version
- Increment version number and rebuild

**ReadTheDocs build fails:**
- Check build logs at https://readthedocs.org/projects/ohdsi-circe-python-alpha/builds/
- Ensure all dependencies are in `docs/requirements.txt`

**Documentation not updating:**
- Trigger manual build: ReadTheDocs project → Versions → Build
- Check webhook: GitHub Settings → Webhooks

---

## 📋 Checklist Before First Release

- [ ] PyPI account created with 2FA enabled
- [ ] API token generated and stored
- [ ] GitHub secret `PYPI_API_TOKEN` added
- [ ] Tests passing: `pytest --cov`
- [ ] Version numbers updated
- [ ] CHANGELOG.md updated
- [ ] README.md reviewed
- [ ] Built package: `python -m build`
- [ ] Checked package: `twine check dist/*`
- [ ] Tested locally
- [ ] ReadTheDocs project imported
- [ ] Ready to push the tag!

---

For detailed information, see [PUBLISHING_GUIDE.md](PUBLISHING_GUIDE.md)
