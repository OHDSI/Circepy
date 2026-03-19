# Ibis Executor Limitations

The `circe.execution` subsystem is experimental and feature-complete for the
currently implemented semantics.

## Custom Era Implementation

✅ **`custom_era` end strategy is now implemented** using SQLGlot transpilation.

The custom era logic is written in a reference SQL dialect (PostgreSQL) and automatically
transpiled to the target backend's SQL dialect using SQLGlot. This provides:
- Cross-dialect compatibility
- Correctness through a single source of truth
- Support for all major SQL databases

**Supported backends for custom era:**
- DuckDB
- PostgreSQL  
- Spark / Databricks
- Snowflake
- BigQuery
- Trino
- MySQL
- SQLite

The executor raises `UnsupportedFeatureError` if custom era is requested on an
unsupported backend.

## Future Enhancements

Potential future improvements:
- Native Ibis implementation (avoiding temp tables)
- Performance optimizations for very large event tables
- Additional era grouping strategies
