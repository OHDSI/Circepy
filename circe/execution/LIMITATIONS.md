# Ibis Executor MVP Limitations

The `circe.execution` subsystem is intentionally scoped as an MVP path and is
not full semantic parity with the legacy SQL builder yet.

Current explicit limitations:

- Concept-set expansion semantics are not implemented:
  - `includeDescendants`
  - `includeMapped`
- Criterion-local `correlated_criteria` is not implemented.
- Demographic criteria groups are not implemented in group evaluation.
- Criterion-level race/ethnicity filtering is not implemented.
- `custom_era` end strategy is not implemented.

The executor raises `UnsupportedFeatureError` when these features are requested,
instead of silently degrading semantics.
