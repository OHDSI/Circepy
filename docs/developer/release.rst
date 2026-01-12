Release Process
===============

See :doc:`../RELEASE_CHECKLIST` for the complete release checklist.

Version Numbers
---------------

We follow Semantic Versioning (MAJOR.MINOR.PATCH).

Release Steps
-------------

1. Update version in pyproject.toml and __init__.py
2. Update CHANGELOG.md
3. Run all tests
4. Build package: ``python -m build``
5. Upload to PyPI: ``twine upload dist/*``

For details, see RELEASE_CHECKLIST.md.

