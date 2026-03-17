# Ibis Execution Subsystem

The `circe.execution` package is an experimental, table-first Ibis executor for
`CohortExpression` models. It runs in parallel with the existing SQL builder.

## Public Functions

- `build_cohort(...)` is the canonical expression-building entrypoint.
- `write_cohort(...)` projects the built relation into OHDSI cohort-table shape,
  then writes or replaces rows for one `cohort_id` while preserving other cohorts.
- `build_cohort_ibis` and `write_cohort_ibis` are transition aliases.

## Layered Architecture

1. `normalize/`
converts public cohort-expression models into frozen internal dataclasses.

2. `lower/`
maps normalized criteria into `EventPlan` objects and reusable plan steps.

3. `ibis/`
compiles plan steps into Ibis table expressions.

4. `engine/`
orchestrates cohort semantics: primary events, criteria groups, inclusion rules,
end strategy, censoring, and collapse.

## Canonical Event Schema

All compiled domain event tables are standardized before cohort orchestration.
Canonical columns are defined in `circe/execution/plan/schema.py` and include:

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

## Codeset Resolution Flow

Codeset expansion is handled by `CachedConceptSetResolver` in
`circe/execution/ibis/codesets.py`.

Resolution behavior:

- direct concept inclusion
- descendant expansion via `concept_ancestor` when requested
- mapped concept expansion via `concept_relationship` (`Maps to`) when requested
- exclusion precedence applied after expansion

The resolver cache is local to an execution context run.

## Current Limitation

- `custom_era` end strategy remains unsupported in this executor path.
