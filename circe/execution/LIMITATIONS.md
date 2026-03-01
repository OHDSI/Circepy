# Ibis Executor MVP Limitations

The `circe.execution` subsystem is intentionally scoped as an MVP path and is
not full semantic parity with the legacy SQL builder yet.

Current explicit limitations:

- `custom_era` end strategy is not implemented.

The executor raises `UnsupportedFeatureError` when these features are requested,
instead of silently degrading semantics.
