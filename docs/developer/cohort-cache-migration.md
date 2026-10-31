# Migrating existing integer-keyed cohorts into the checksum cache

The new runner stores generated rows in a checksum-keyed cache and writes the
study-facing integer cohort table only as a copy step. Existing integer-keyed
tables cannot be reused automatically because they do not carry the canonical
definition checksum.

This note is for migrating cohorts that were already generated before the cache
redesign.

## Cache layout

```text
cache.cohort_cache (
    cohort_checksum   VARCHAR,
    subject_id        BIGINT,
    cohort_start_date DATE,
    cohort_end_date   DATE
)

cache.cohort_cache_registry (
    cohort_checksum   VARCHAR,
    completed         BOOLEAN,
    row_count         BIGINT,
    updated_at        TIMESTAMP,
    completed_at      TIMESTAMP
)
```

One cache entry exists per canonical checksum, not per integer cohort id.

## Checksum

Use the same canonical checksum as the runner:

```python
from circe.decomposition import semantic_expression_key

checksum = semantic_expression_key(definition.expression, include_title=False)
```

Do not use the old registry checksum unless it was generated with the same
canonicalisation rules.

## Migration procedure

1. Stop new generation/writes against the old cohort table.
2. Load the original cohort definitions (JSON + CSV) so each old integer id can
   be mapped to an expression and a canonical checksum.
3. Group integer ids by checksum. If several integer ids share a checksum,
   verify that their old rows are identical with a two-way `EXCEPT ALL`; keep one
   copy of the rows.
4. Copy each unique checksum's rows into `cache.cohort_cache`:

```sql
INSERT INTO cache.cohort_cache
    (cohort_checksum, subject_id, cohort_start_date, cohort_end_date)
SELECT
    '<checksum>', subject_id, cohort_start_date, cohort_end_date
FROM old_results.cohort
WHERE cohort_definition_id = <old_integer_id>;
```

5. Insert or upsert the cache registry row only when the old cohort was complete:

```sql
INSERT INTO cache.cohort_cache_registry
    (cohort_checksum, completed, row_count, updated_at, completed_at)
VALUES
    ('<checksum>', TRUE, <row_count>, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
```

6. Ignore the old per-shard registries (`..._registry_sNNN`) and the old
   integer-keyed registry. They are not consulted by the cache path and can be
   dropped after validation.
7. Validate cache counts and row equality per checksum.
8. Run the new cache path with `reuse_existing=true`; it should copy cached
   checksums into the integer-id output table without regenerating them.

## Important constraints

- Do not migrate partial or failed cohorts. Leave them absent/incomplete and
  let the new runner regenerate them.
- Do not insert duplicate cache rows for repeated integer ids using the same
  checksum.
- The final study cohort table remains integer-keyed for HADES/CohortGenerator;
  only the cache is checksum-keyed.
- Cache rows are person-level data. Use the same access controls and retention
  policy as the old results schema.
