# Execution Architecture

This document describes the design of the new `circe.execution` subsystem and
the intended boundaries between its layers.

## Purpose

The execution subsystem provides a backend-native, relation-first way to
evaluate `CohortExpression` models.

The design goals are:

- keep cohort semantics explicit and testable
- separate model normalization from backend compilation
- standardize domain events before orchestration
- make backend materialization a thin outer layer, not the core engine

## Public Contract

The public entrypoints are:

- `build_cohort(...)`
- `write_cohort(...)`

`build_cohort(...)` returns a lazy Ibis relation in the canonical execution
shape.

`write_cohort(...)` projects the built relation into OHDSI cohort-table shape
and writes rows for one `cohort_id`.

The write contract is cohort-scoped:

- `if_exists="fail"` errors only if rows already exist for that `cohort_id`
- `if_exists="replace"` replaces only that `cohort_id`'s rows and preserves
  rows for other cohorts in the same target table

## Layered Design

The subsystem is intentionally split into five layers.

### 1. `normalize/`

Responsibility:

- convert public cohort-definition models into frozen internal dataclasses
- remove aliasing and optional-shape noise from downstream code
- reject explicitly unsupported semantics early

Output:

- normalized cohort, criteria, groups, windows, and end-strategy objects

### 2. `lower/`

Responsibility:

- turn normalized criteria into backend-agnostic execution plans
- encode reusable event and predicate planning logic
- keep domain-specific lowering separate from backend-specific compilation

Output:

- `EventPlan` objects and normalized predicate/planning structures

### 3. `ibis/`

Responsibility:

- compile lowered plans into Ibis relations
- standardize domain tables into the canonical event schema
- resolve concept sets and person filters
- provide backend operations used by the public write path

Output:

- canonical Ibis relations ready for cohort orchestration

### 4. `engine/`

Responsibility:

- evaluate cohort semantics over canonical event relations
- handle primary events, additional criteria, inclusion rules, censoring,
  limits, collapse, and end strategy

This layer owns cohort logic. It should not need to know OMOP source-table
details once relations have been standardized.

### 5. API materialization layer

Responsibility:

- connect public API calls to normalization, compilation, and engine execution
- project final relations into OHDSI cohort-table shape
- handle backend table existence checks and cohort-scoped writes

This is intentionally thin. It should orchestrate layers, not re-implement
their logic.

## Canonical Event Schema

Compiled domain event relations are standardized before engine orchestration.
The canonical columns are defined in `circe/execution/plan/schema.py`.

Important columns include:

- `person_id`
- `event_id`
- `start_date`
- `end_date`
- `domain`
- `concept_id`
- `source_concept_id`
- `visit_occurrence_id`
- `criterion_index`
- `criterion_type`
- `source_table`

This standardization is one of the main design differences from the legacy
builder-based path. The engine operates on one event shape instead of many
domain-specific SQL-builder shapes.

## Data Flow

The end-to-end flow is:

1. `CohortExpression`
2. normalize to frozen internal dataclasses
3. lower criteria into event/predicate plans
4. compile plans into canonical Ibis relations
5. run cohort semantics in `engine/`
6. optionally materialize to OHDSI cohort-table rows

## Codeset Resolution

Codeset expansion is handled by `CachedConceptSetResolver`.

Resolution semantics are:

- direct inclusion
- descendant expansion through `concept_ancestor`
- mapped concept expansion through `concept_relationship`
- exclusion precedence after expansion

The cache is scoped to one execution context.

## What This Replaced

This redesign intentionally replaces the older mutable builder/context-based
execution path.

Removed or reduced surfaces include:

- the legacy builder tree under `circe.execution.builders`
- the old builder-context shell
- the old compatibility-heavy execution surface
- the Polars-oriented compatibility layer

The new subsystem is function-first rather than executor-object-first.

## Migration Notes

If you used the legacy execution prototype:

- use `build_cohort(...)` to get the lazy relation
- use backend operations on that relation for inspection and collection
- use `write_cohort(...)` for cohort-table writes

In other words:

- SQL/dataframe inspection now happens via the returned relation and backend
- write semantics now live in `write_cohort(...)`, not a mutable executor
  object

## Current Explicit Limitation

- `custom_era` end strategy is not implemented in this execution path

Unsupported semantics should fail explicitly with execution-layer errors rather
than silently degrading behavior.

## Test Strategy

The intended test organization for this subsystem is documented in
`circe/execution/TESTING.md`.

That document splits tests by layer:

- normalization/lowering unit tests
- Ibis helper unit tests
- engine semantics integration tests
- public API/wiring tests
- explicit error/limitation tests

## Reviewer Guidance

For code review, the most useful way to read the subsystem is:

1. `circe/execution/api.py`
2. `circe/execution/README.md`
3. `circe/execution/TESTING.md`
4. `normalize/`
5. `lower/`
6. `ibis/`
7. `engine/`

That order matches the intended architecture rather than the directory listing.
