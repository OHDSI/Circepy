# Ibis Executor Limitations

The `circe.execution` subsystem is experimental and feature-complete for the
currently implemented semantics.

Current explicit limitations:

- `custom_era` end strategy is not implemented.

The executor raises `UnsupportedFeatureError` when these features are requested,
instead of silently degrading semantics.
