# Agent Guide

This repository is a Python implementation of OHDSI CIRCE-BE. Before pushing any
change, run the local CI preflight harness so you catch CI failures without a
GitHub Actions round trip.

## Fast path

```bash
# 1. Record the test baseline at the start of a task
pytest -n auto --tb=short -v --json-report --json-report-file=.test_baseline.json

# ... make changes ...

# 2. Run the full CI-equivalent preflight before pushing
python scripts/ci_preflight.py --refresh
```

The harness reproduces the GitHub Actions gates and catches three classes of
failure that a plain local `pytest` + `pre-commit` run misses:

- **Tool-version skew** — CI installs the latest `ruff`; local `pre-commit` pins
  an older one. The `lint` gate always runs the latest ruff.
- **Dependency drift** — CI resolves the latest allowed dependencies and ignores
  `uv.lock`, so an upstream regression (e.g. `sqlglot`) can break the suite. The
  `tests` gate installs/upgrades an isolated env first and prints the resolved
  versions of sensitive packages.
- **Coverage thresholds** — Codecov patch/project failures. The `coverage` gate
  computes both from `coverage.xml`.

Run a subset with `--only lint tests` or `--skip coverage`. See
[`scripts/README.md`](scripts/README.md) for all options.

## Things that have bitten us

- **Pin transitive deps when an upstream release regresses your tests.** CI
  ignores `uv.lock`, so a broken latest release will fail CI even when your env
  is green. Add an upper bound in `pyproject.toml` and `tox.ini` and document it.
- **`pre-commit` is not a git subcommand.** Use `pre-commit run --all-files`.
- **Newer ruff formats code inside Markdown code fences.** If the lint gate
  flags a tracked `.md` file, run `uvx ruff format <file>`.
- **Stage new files before preflight.** The `lint` gate excludes untracked files
  to mirror a clean CI checkout.

## Repository conventions

- Full agent instructions live in [`CLAUDE.md`](CLAUDE.md); contributor workflow
  lives in [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Do not bypass the ibis lazy-execution rules in `CLAUDE.md` (never pull large
  result sets into Python memory in production code).
- Do not run `git commit` unless explicitly asked.
