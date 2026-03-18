# Execution Testing Strategy

The new `circe.execution` engine should be tested in layers, with each layer
optimized for a different failure mode.

## Goals

- Keep the engine safe to refactor while the design is still evolving.
- Make regressions easy to localize to one layer.
- Avoid turning the test suite into a single large DuckDB integration harness.

## Test Layers

1. Pure normalization and lowering unit tests

- Scope: `normalize/`, `lower/`, `plan/`, small pure helpers.
- Style: no backend, no SQL execution, frozen dataclass assertions.
- Current files:
  - `tests/execution/test_normalize.py`
  - `tests/execution/test_normalize_contracts.py`
  - `tests/execution/test_lowering.py`
  - `tests/execution/test_lower_contracts.py`
  - `tests/execution/test_compile_contracts.py`

2. Ibis helper unit tests

- Scope: `ibis/codesets.py`, `ibis/operations.py`, `ibis/context.py`,
  `ibis/standardize.py`, `engine/*` helpers that do not need full cohort runs.
- Style: fake backends where possible; DuckDB only when expression execution is
  the thing under test.
- Current files:
  - `tests/execution/test_context_wiring.py`
  - `tests/execution/test_operations.py`
  - `tests/execution/test_ibis_compat.py`
  - `tests/execution/test_group_demographics.py`
  - `tests/execution/test_person_filters.py`

3. Engine semantics integration tests

- Scope: primary events, correlated criteria, groups, inclusion rules, result
  limits, end strategy, censoring, parity-sensitive orchestration.
- Style: minimal DuckDB fixtures with only the columns required for the
  behavior under test.
- Current files:
  - `tests/execution/test_groups.py`
  - `tests/execution/test_inclusion.py`
  - `tests/execution/test_result_limits.py`
  - `tests/execution/test_end_strategy_censoring.py`
  - `tests/execution/test_parity_regressions.py`

4. Public API and wiring tests

- Scope: `build_cohort`, `write_cohort`, package exports, compat shims.
- Style: verify entrypoint behavior, argument handling, and write semantics
  without duplicating engine internals.
- Current files:
  - `tests/execution/test_api_public.py`
  - `tests/execution/test_api_ibis.py`
  - `tests/execution/test_scaffolding.py`

5. Error and limitation tests

- Scope: explicit unsupported features, validation messages, and backend
  capability failures.
- Style: assert on error type and message text where the API contract matters.
- Current files:
  - `tests/execution/test_error_messages.py`

## Rules

- Each new execution module should get at least one direct test file in the
  same layer as its responsibility.
- Prefer fake backends for capability/error branches, and DuckDB for relational
  behavior.
- Keep fixtures local to a test file unless three or more files need the same
  setup.
- When adding a new feature, add:
  - one layer-local unit/helper test
  - one end-to-end or API-level assertion if the feature crosses layers
- Parity/regression tests should stay small and named after the bug or contract
  they protect.

## Local Gate

Use this as the normal execution-engine check:

```bash
uv run pre-commit run --all-files
uv run pytest tests/execution -q
```

Before merging broader refactors, also run:

```bash
uv run pytest
```
