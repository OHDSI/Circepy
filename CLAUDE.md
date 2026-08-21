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

## Ibis Execution Layer: NEVER use Python in-memory operations

The datasets this software processes are large (often 100M+ rows). Operations that pull data into Python memory will crash the process. All data processing MUST remain as lazy ibis expressions executed on the database backend.

### Forbidden patterns in production code (`circe/execution/` and `circe/cohort_definition_set/`):

| Pattern | Example (NEVER do this) | Instead |
|---|---|---|
| `.execute()` | `table.execute()` loads entire table into a pandas DataFrame in memory | Compose ibis expressions; let the backend execute the full query |
| `.to_pandas()` | `table.to_pandas()` pulls result set into Python | Use ibis expressions; only call `.execute()` for small scalars (e.g., `table.limit(1).count().execute()`) |
| Python iteration over results | `for row in table.select(...).distinct().to_pandas().itertuples()` | Push aggregation/distinct into ibis; use window functions or joins |
| `ibis.memtable()` with large DataFrames | Constructing a large `pd.DataFrame` and passing to `ibis.memtable()` | Read directly from the database table (passed tables already exist in the backend) |
| Loading files into Python | `pd.read_csv(...)`, reading Parquet into memory | Use ibis to read files: `ibis.read_csv()`, `ibis.read_parquet()` |

### Existing violations in production code (DO NOT FIX — examples for reference):

1. **`circe/cohort_definition_set/_checksum_store.py`** — uses `pandas`, `.execute()`, `pd.DataFrame()`, row iteration — should use ibis expressions end-to-end
2. **`circe/execution/engine/custom_era.py:86`** — `.execute().iloc[:, 0]` to pull concept IDs into a Python tuple
3. **`circe/execution/engine/group_demographics.py:97`** — `.to_pandas().itertuples()` to iterate over distinct concept IDs
4. **`circe/execution/ibis/operations.py:86`** — `.execute()` to check if rows exist (use `table.limit(1).count()` instead)
5. **`benchmarks/compare_cohort_outputs.py`** — full table `.execute()`, pandas row iteration, set comparison in memory

### Allowed uses of `.execute()`:

- **Tests only** — tests run against small in-memory DuckDB databases with tiny fixtures. Assertions on small result sets are fine.
- **Scalar values** — getting a single count or checking existence: `table.count().execute()`, `table.limit(1).execute()` (only returns 1 row)

When writing new production code, if you find yourself reaching for `.execute()`, `.to_pandas()`, or Python iteration over ibis results, **stop** — the query can be rewritten as a lazy ibis expression.

## Git Workflow
- Do not run `git commit` — the user will handle commits
- Run pre-commit checks to validate code quality before marking tasks complete
