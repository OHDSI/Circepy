# Claude Instructions for circepy

## Python Environment
- Always use virtualenv for Python operations (don't rely on system Python or unauthenticated pip installs)
- Activate the virtual environment before running Python commands or installing packages

## Pre-completion Checklist
Before completing any task, run git pre-commit checks:
```bash
git pre-commit run --all-files
```

If pre-commit checks fail, fix the issues and re-run until they pass.

## Git Workflow
- Do not run `git commit` — the user will handle commits
- Run pre-commit checks to validate code quality before marking tasks complete
