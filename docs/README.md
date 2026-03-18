# CIRCE Python Documentation

This directory contains the Sphinx documentation for CIRCE Python.

## Building Documentation

### Install Dependencies

```bash
uv sync --extra docs
```

Or, if you are not using `uv`:

```bash
pip install -e ".[docs]"
```

### Build HTML Documentation

```bash
uv run make -C docs html
```

The generated HTML will be in `docs/_build/html/`. Open `docs/_build/html/index.html` in your browser.

### Build PDF Documentation

```bash
uv run make -C docs latexpdf
```

### Clean Build Files

```bash
uv run make -C docs clean
```

## Documentation Structure

* **Getting Started**: Installation, quick start, CLI guide
* **User Guide**: Concepts, cohort definitions, SQL generation, validation, examples
* **API Reference**: Complete API documentation with autodoc
* **Developer Guide**: Contributing, architecture, testing, release process
* **Additional**: FAQ, troubleshooting, changelog, license

## Live Documentation

Once published, documentation will be available at:
https://ohdsi-circe-python-alpha.readthedocs.io/

## Contributing to Documentation

1. Edit `.rst` files in the `docs/` directory
2. Build locally to preview changes
3. Submit pull request with documentation updates

## Documentation Standards

* Use reStructuredText (`.rst`) format
* Include code examples with proper syntax highlighting
* Link between pages using `:doc:` role
* Auto-generate API docs with autodoc directives
* Keep examples up-to-date with package changes
