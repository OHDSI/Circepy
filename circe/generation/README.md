# Generation Layer

`circe.generation` adds policy-driven, metadata-aware cohort generation on top of the
low-level execution API.

## Public Functions

- `create_generation_tables(...)`
- `generate_cohort(...)`
- `generate_cohort_set(...)`
- `get_generated_cohort_status(...)`
- `apply_subset(...)`
- `generate_subset(...)`
- `get_generated_cohort_counts(...)`
- `validate_generated_cohort(...)`

## Design

- Keeps execution primitive unchanged: `build_cohort(...) -> relation`.
- Applies generation policies in this layer: `fail`, `replace`, `skip_if_same`, `replace_if_changed`.
- Uses deterministic fingerprints for incremental generation.
- Stores metadata and checksums in dedicated tables.
- Compiles subset definitions as relation transforms, then materializes by policy.

## Incremental Fingerprinting

- Default behavior is **definition/dependency-aware** only.
- `replace_if_changed` reacts to:
  - cohort/subset definition changes
  - relevant options changes
  - dependency checksum changes
  - engine/schema version changes
- Default behavior is **not** automatically source-data-aware.
- Opt-in data-aware invalidation is supported via `data_version_token`.
  - When provided, the token is included in generation checksums.
  - When omitted, source data changes alone do not trigger regeneration.

## Metadata Tables

- `cohort_generation_metadata`
- `cohort_generation_checksums`
- `cohort_subset_metadata`

## Current Scope

- Generation and incremental regeneration for single cohorts and cohort sets.
- Subset operators:
  - demographic
  - limit
  - cohort relationship (intersect, exclude, require_overlap)
- Dependency-aware subset checksums include parent/referenced cohort checksums.

## Known Limitations

- Subset operators currently target canonical OMOP cohort table columns.
- Subset metadata dependency payload is JSON-serialized text for portability.
- Metadata/checksum upserts currently rewrite whole tables (portable MVP path).
