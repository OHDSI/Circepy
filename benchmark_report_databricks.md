# Cohort Generation Execution Benchmark (Databricks)

*Date generated:* 2026-03-18 19:13:18.096735

This report compares the execution time of cohort generation on **Databricks** between the traditional **CirceR (Java + SqlRender)** and the new **circe_py (Python + Ibis)** implementation.

## Benchmark Configuration

- **Pre-compilation**: Both approaches pre-compile SQL/relations before execution
- **Validation**: Python uses `skip_validation=TRUE` to bypass table/row checks (matches Java behavior)
- **Spark Optimizations**: Adaptive query execution, partition coalescing, and broadcast joins enabled
- **Iterations**: Each cohort benchmarked with identical parameters

### Aggregate Performance
- **CirceR/Java Average Median Time:** 48.78 ms
- **CircePy/Ibis Average Median Time:** 21.62 ms

> **Conclusion:** `circe_py` (Ibis) is generally **faster** than Circe-be/`SqlRender` by **~55.7%** when evaluating identically generated cohorts.

### Raw Results
| Cohort | Approach | Min | lq | Mean | Median | uq | Max | Neval |
|---|---|---|---|---|---|---|---|---|
| 10.json | CirceR_Java_Databricks | 53.26 | 53.26 | 53.26 | 53.26 | 53.26 | 53.26 | 1 |
|  | CircePy_Ibis_Databricks | 41.86 | 41.86 | 41.86 | 41.86 | 41.86 | 41.86 | 1 |
| 100.json | CirceR_Java_Databricks | 50.24 | 50.24 | 50.24 | 50.24 | 50.24 | 50.24 | 1 |
|  | CircePy_Ibis_Databricks | 26.66 | 26.66 | 26.66 | 26.66 | 26.66 | 26.66 | 1 |
| 1000.json | CirceR_Java_Databricks | 50.52 | 50.52 | 50.52 | 50.52 | 50.52 | 50.52 | 1 |
|  | CircePy_Ibis_Databricks | 15.47 | 15.47 | 15.47 | 15.47 | 15.47 | 15.47 | 1 |
| 1001.json | CirceR_Java_Databricks | 59.03 | 59.03 | 59.03 | 59.03 | 59.03 | 59.03 | 1 |
|  | CircePy_Ibis_Databricks | 37.61 | 37.61 | 37.61 | 37.61 | 37.61 | 37.61 | 1 |
| 1002.json | CirceR_Java_Databricks | 33.83 | 33.83 | 33.83 | 33.83 | 33.83 | 33.83 | 1 |
|  | CircePy_Ibis_Databricks | 9.94 | 9.94 | 9.94 | 9.94 | 9.94 | 9.94 | 1 |
| 1003.json | CirceR_Java_Databricks | 33.42 | 33.42 | 33.42 | 33.42 | 33.42 | 33.42 | 1 |
|  | CircePy_Ibis_Databricks | 11.35 | 11.35 | 11.35 | 11.35 | 11.35 | 11.35 | 1 |
| 1004.json | CirceR_Java_Databricks | 38.99 | 38.99 | 38.99 | 38.99 | 38.99 | 38.99 | 1 |
|  | CircePy_Ibis_Databricks | 11.68 | 11.68 | 11.68 | 11.68 | 11.68 | 11.68 | 1 |
| 1005.json | CirceR_Java_Databricks | 55.79 | 55.79 | 55.79 | 55.79 | 55.79 | 55.79 | 1 |
|  | CircePy_Ibis_Databricks | 20.65 | 20.65 | 20.65 | 20.65 | 20.65 | 20.65 | 1 |
| 1006.json | CirceR_Java_Databricks | 69.09 | 69.09 | 69.09 | 69.09 | 69.09 | 69.09 | 1 |
|  | CircePy_Ibis_Databricks | 19.52 | 19.52 | 19.52 | 19.52 | 19.52 | 19.52 | 1 |
| 1007.json | CirceR_Java_Databricks | 43.67 | 43.67 | 43.67 | 43.67 | 43.67 | 43.67 | 1 |
|  | CircePy_Ibis_Databricks | 21.49 | 21.49 | 21.49 | 21.49 | 21.49 | 21.49 | 1 |
