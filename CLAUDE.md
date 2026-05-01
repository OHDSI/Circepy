# Claude Instructions for circepy

## Python Environment
- Always use virtualenv for Python operations (don't rely on system Python or unauthenticated pip installs)
- Activate the virtual environment before running Python commands or installing packages

## Starting tasks - record testing state

At the start of any task, record the state of tests as a baseline. It is not your job to fix pre-existing issues unless otherwise specified.

Run tests with multiprocess for speed and store the state:
```bash
pytest -n auto --tb=short -v --json-report --json-report-file=.test_baseline.json
```

If the test state file is not created, check that pytest-xdist and pytest-json-report are installed in the virtualenv.

## Pre-completion Checklist
Before completing any task:

1. Re-run pytest to verify no regressions:
```bash
pytest -n auto --tb=short -v --json-report --json-report-file=.test_final.json
```

Compare `.test_baseline.json` with `.test_final.json` — the final state should not show new failures.

2. Run git pre-commit checks:
```bash
git pre-commit run --all-files
```

If pre-commit checks fail, fix the issues and re-run until they pass.

## Git Workflow
- Do not run `git commit` — the user will handle commits
- Run pre-commit checks to validate code quality before marking tasks complete
