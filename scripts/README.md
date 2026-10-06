# Developer scripts

## `ci_preflight.py` — local CI preflight harness

Reproduces the checks GitHub Actions runs so you can catch failures **before**
pushing and waiting on a CI round trip. It exists because three classes of
failure only ever showed up in CI:

| Failure class | Why it only appeared in CI | How the harness catches it |
|---|---|---|
| **Tool-version skew** | CI installs the *latest* `ruff`; local `pre-commit` pins an older one. Code can satisfy one and fail the other. | The `lint` gate always runs the latest ruff (`uvx ruff@latest`), then the pinned `pre-commit`. |
| **Dependency drift** | CI resolves the *latest allowed* transitive deps and ignores `uv.lock`, so a regression in e.g. `sqlglot` breaks the suite. | The `tests` gate installs/upgrades into an isolated env (`.ci_preflight/venv`) before running, and prints resolved versions of sensitive packages. |
| **Coverage thresholds** | Codecov fails a PR when patch coverage is below target or project coverage regresses. | The `coverage` gate computes project + patch coverage from `coverage.xml` against configurable targets. |

### Usage

```bash
# Run every gate (lint, pre-commit, tests, coverage)
python scripts/ci_preflight.py

# Recreate the isolated env with the newest allowed dependencies (drift check)
python scripts/ci_preflight.py --refresh

# Run a subset
python scripts/ci_preflight.py --only lint coverage
python scripts/ci_preflight.py --skip tests

# Use the current interpreter instead of an isolated env
python scripts/ci_preflight.py --no-install

# Compare the run against .test_baseline.json (recorded at task start)
python scripts/ci_preflight.py --compare-baseline

# Override thresholds / base ref / python
python scripts/ci_preflight.py --patch-target 90 --base-ref origin/main --python 3.12
```

Exit code is non-zero if any gate fails. Thresholds and defaults live under
`[tool.ci-preflight]` in `pyproject.toml`.

### Notes

- Ruff runs in directory mode (like CI's `ruff check .`) but **excludes
  untracked files**, so scratch documents in your working copy don't produce
  false positives a clean CI checkout would never see. `git add` new files
  before running the harness so they are linted.
- The isolated test env lives in `.ci_preflight/` (git-ignored).
- Newer ruff releases format code inside Markdown code fences. If a tracked
  `.md` file trips the format gate, run `uvx ruff format <file>`.

### Public API (importable helpers)

The pure helpers are importable and unit-tested in `tests/test_ci_preflight.py`:

- `parse_changed_lines`, `parse_coverage_xml`, `compute_patch_coverage`,
  `compute_project_coverage`, `percentage`
- `parse_test_report`, `new_failures`, `parse_pip_versions`, `load_config`
