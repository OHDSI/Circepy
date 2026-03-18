# Cohort Generation Execution Benchmark

*Date generated:* 2026-03-18 14:24:28.792419

This report compares the execution time of cohort generation between the traditional **CirceR (Java + T-SQL)** and the new **circe_py (Python + Ibis)** implementation.

### Aggregate Performance
- **CirceR/Java Average Median Time:** 19.30 ms
- **CircePy/Ibis Average Median Time:** 18.85 ms

> **Conclusion:** `circe_py` (Ibis) is generally **faster** than `SqlRender` by **~2.3%** when evaluating identically generated cohorts.

### Raw Results
| Cohort | Approach | Min | lq | Mean | Median | uq | Max | Neval |
|---|---|---|---|---|---|---|---|---|
| 10.json | CirceR_Java_DBI | 13.90 | 14.10 | 15.17 | 14.40 | 15.90 | 18.44 | 10 |
|  | CircePy_Ibis_DuckDB | 4.48 | 4.58 | 5.47 | 5.21 | 6.28 | 7.43 | 10 |
| 100.json | CirceR_Java_DBI | 23.87 | 24.86 | 27.73 | 27.13 | 29.68 | 33.68 | 10 |
|  | CircePy_Ibis_DuckDB | 10.41 | 11.21 | 12.46 | 12.40 | 13.83 | 14.40 | 10 |
| 1000.json | CirceR_Java_DBI | 12.55 | 12.67 | 13.46 | 13.01 | 13.90 | 15.70 | 10 |
|  | CircePy_Ibis_DuckDB | 2.96 | 3.25 | 3.51 | 3.52 | 3.60 | 4.18 | 10 |
| 1001.json | CirceR_Java_DBI | 13.38 | 13.56 | 14.38 | 14.24 | 14.47 | 17.32 | 10 |
|  | CircePy_Ibis_DuckDB | 3.53 | 3.82 | 4.17 | 4.04 | 4.28 | 5.66 | 10 |
| 1002.json | CirceR_Java_DBI | 13.08 | 13.56 | 14.08 | 14.09 | 14.54 | 15.20 | 10 |
|  | CircePy_Ibis_DuckDB | 2.93 | 3.01 | 3.35 | 3.39 | 3.65 | 3.78 | 10 |
| 1003.json | CirceR_Java_DBI | 10.94 | 11.31 | 12.26 | 11.55 | 12.06 | 15.87 | 10 |
|  | CircePy_Ibis_DuckDB | 4.93 | 5.53 | 6.57 | 5.68 | 6.88 | 12.75 | 10 |
| 1004.json | CirceR_Java_DBI | 11.22 | 11.73 | 13.00 | 12.40 | 13.43 | 16.80 | 10 |
|  | CircePy_Ibis_DuckDB | 4.64 | 5.08 | 5.50 | 5.44 | 5.65 | 7.15 | 10 |
| 1005.json | CirceR_Java_DBI | 14.40 | 14.71 | 16.63 | 16.11 | 18.71 | 19.41 | 10 |
|  | CircePy_Ibis_DuckDB | 3.87 | 4.15 | 4.65 | 4.29 | 4.45 | 8.27 | 10 |
| 1006.json | CirceR_Java_DBI | 17.88 | 19.09 | 23.73 | 22.73 | 27.82 | 36.86 | 10 |
|  | CircePy_Ibis_DuckDB | 4.05 | 4.36 | 5.27 | 5.19 | 5.70 | 7.24 | 10 |
| 1007.json | CirceR_Java_DBI | 27.90 | 29.12 | 31.12 | 29.98 | 31.89 | 37.63 | 10 |
|  | CircePy_Ibis_DuckDB | 19.45 | 19.87 | 24.08 | 23.85 | 25.21 | 34.15 | 10 |
| 1009.json | CirceR_Java_DBI | 51.96 | 52.18 | 54.75 | 53.13 | 57.70 | 60.11 | 10 |
|  | CircePy_Ibis_DuckDB | 109.65 | 118.49 | 126.79 | 123.25 | 135.94 | 146.27 | 10 |
| 1010.json | CirceR_Java_DBI | 15.56 | 15.90 | 16.91 | 16.52 | 17.45 | 20.41 | 10 |
|  | CircePy_Ibis_DuckDB | 32.26 | 34.48 | 36.62 | 35.08 | 37.44 | 47.88 | 10 |
| 1011.json | CirceR_Java_DBI | 11.31 | 11.76 | 12.08 | 12.06 | 12.42 | 13.06 | 10 |
|  | CircePy_Ibis_DuckDB | 4.98 | 5.18 | 5.56 | 5.59 | 6.04 | 6.15 | 10 |
| 1012.json | CirceR_Java_DBI | 11.65 | 11.82 | 12.64 | 12.12 | 12.89 | 16.19 | 10 |
|  | CircePy_Ibis_DuckDB | 5.59 | 5.81 | 6.13 | 6.11 | 6.27 | 6.86 | 10 |
| 1013.json | CirceR_Java_DBI | 11.42 | 11.77 | 12.29 | 12.32 | 12.92 | 13.18 | 10 |
|  | CircePy_Ibis_DuckDB | 4.86 | 5.37 | 5.48 | 5.41 | 5.74 | 6.14 | 10 |
| 1016.json | CirceR_Java_DBI | 14.41 | 14.75 | 18.62 | 16.87 | 20.66 | 30.34 | 10 |
|  | CircePy_Ibis_DuckDB | 7.85 | 9.19 | 10.87 | 9.60 | 13.18 | 18.71 | 10 |
| 1017.json | CirceR_Java_DBI | 11.96 | 12.23 | 12.91 | 12.67 | 13.50 | 15.13 | 10 |
|  | CircePy_Ibis_DuckDB | 6.49 | 6.75 | 7.40 | 7.11 | 7.35 | 10.22 | 10 |
| 1018.json | CirceR_Java_DBI | 11.65 | 12.45 | 14.46 | 13.53 | 15.68 | 21.79 | 10 |
|  | CircePy_Ibis_DuckDB | 4.56 | 5.07 | 7.10 | 5.34 | 8.30 | 12.47 | 10 |
| 1019.json | CirceR_Java_DBI | 16.19 | 17.09 | 18.92 | 17.54 | 19.98 | 25.55 | 10 |
|  | CircePy_Ibis_DuckDB | 16.94 | 17.45 | 19.03 | 18.22 | 21.05 | 22.03 | 10 |
| 1020.json | CirceR_Java_DBI | 26.52 | 28.96 | 37.04 | 34.96 | 44.87 | 51.18 | 10 |
|  | CircePy_Ibis_DuckDB | 18.99 | 19.20 | 22.83 | 19.41 | 24.89 | 35.34 | 10 |
| 1021.json | CirceR_Java_DBI | 21.82 | 24.82 | 33.44 | 29.32 | 42.61 | 51.70 | 10 |
|  | CircePy_Ibis_DuckDB | 40.08 | 46.80 | 55.84 | 53.25 | 69.19 | 72.25 | 10 |
| 1022.json | CirceR_Java_DBI | 19.17 | 21.31 | 27.71 | 22.62 | 35.44 | 49.43 | 10 |
|  | CircePy_Ibis_DuckDB | 24.18 | 24.78 | 27.38 | 26.16 | 28.88 | 36.16 | 10 |
| 1023.json | CirceR_Java_DBI | 25.40 | 27.33 | 28.62 | 28.36 | 29.49 | 32.65 | 10 |
|  | CircePy_Ibis_DuckDB | 38.29 | 38.63 | 40.16 | 39.66 | 40.84 | 45.80 | 10 |
| 1024.json | CirceR_Java_DBI | 17.94 | 19.07 | 22.18 | 20.38 | 24.48 | 32.79 | 10 |
|  | CircePy_Ibis_DuckDB | 21.80 | 22.29 | 24.13 | 22.64 | 23.39 | 36.53 | 10 |
| 1025.json | CirceR_Java_DBI | 29.39 | 30.29 | 31.92 | 30.97 | 32.82 | 37.89 | 10 |
|  | CircePy_Ibis_DuckDB | 34.85 | 36.47 | 39.93 | 38.42 | 43.38 | 52.41 | 10 |
| 1026.json | CirceR_Java_DBI | 13.14 | 14.88 | 20.48 | 16.16 | 25.98 | 43.50 | 10 |
|  | CircePy_Ibis_DuckDB | 5.78 | 6.12 | 6.71 | 6.39 | 7.23 | 8.68 | 10 |
| 1027.json | CirceR_Java_DBI | 11.86 | 12.30 | 12.68 | 12.70 | 13.13 | 13.49 | 10 |
|  | CircePy_Ibis_DuckDB | 5.24 | 5.54 | 5.69 | 5.68 | 5.88 | 6.15 | 10 |
| 1028.json | CirceR_Java_DBI | 12.69 | 13.13 | 13.69 | 13.37 | 13.62 | 16.58 | 10 |
|  | CircePy_Ibis_DuckDB | 4.22 | 4.68 | 4.99 | 4.95 | 5.48 | 5.89 | 10 |
| 1029.json | CirceR_Java_DBI | 13.26 | 13.40 | 15.09 | 14.42 | 14.89 | 22.23 | 10 |
|  | CircePy_Ibis_DuckDB | 51.15 | 51.99 | 56.75 | 53.93 | 55.72 | 78.29 | 10 |
| 1030.json | CirceR_Java_DBI | 12.27 | 12.96 | 13.62 | 13.43 | 14.31 | 15.24 | 10 |
|  | CircePy_Ibis_DuckDB | 5.82 | 6.05 | 6.33 | 6.38 | 6.54 | 6.76 | 10 |
