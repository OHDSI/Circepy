# FeatureExtraction parity

Comparisons: **42**, exact matches: **42**

| Cohort | Size | Window | Feature | Era cache | FeatureExtraction | Exact |
|---|---:|---|---|---:|---:|:---:|
| first T2DM | 285,338 | 365 days prior | Type 2 diabetes | 285,338 | 285,338 | yes |
| first T2DM | 285,338 | 365 days prior | Heart failure | 514 | 514 | yes |
| first T2DM | 285,338 | 365 days prior | Obesity | 10,799 | 10,799 | yes |
| first T2DM | 285,338 | 365 days prior | Asthma | 20,102 | 20,102 | yes |
| first T2DM | 285,338 | 365 days prior | Chronic kidney disease | 19,527 | 19,527 | yes |
| first T2DM | 285,338 | 365 days prior | COPD | 3,824 | 3,824 | yes |
| first obesity | 48,673 | 365 days prior | Type 2 diabetes | 34,724 | 34,724 | yes |
| first obesity | 48,673 | 365 days prior | Heart failure | 211 | 211 | yes |
| first obesity | 48,673 | 365 days prior | Obesity | 48,673 | 48,673 | yes |
| first obesity | 48,673 | 365 days prior | Asthma | 7,673 | 7,673 | yes |
| first obesity | 48,673 | 365 days prior | Chronic kidney disease | 8,191 | 8,191 | yes |
| first obesity | 48,673 | 365 days prior | COPD | 1,654 | 1,654 | yes |
| first obesity | 48,673 | 90 days prior | Type 2 diabetes | 23,376 | 23,376 | yes |
| first obesity | 48,673 | 90 days prior | Heart failure | 74 | 74 | yes |
| first obesity | 48,673 | 90 days prior | Obesity | 48,673 | 48,673 | yes |
| first obesity | 48,673 | 90 days prior | Asthma | 3,423 | 3,423 | yes |
| first obesity | 48,673 | 90 days prior | Chronic kidney disease | 3,847 | 3,847 | yes |
| first obesity | 48,673 | 90 days prior | COPD | 697 | 697 | yes |
| first CKD | 82,138 | 365 days prior | Type 2 diabetes | 57,967 | 57,967 | yes |
| first CKD | 82,138 | 365 days prior | Heart failure | 364 | 364 | yes |
| first CKD | 82,138 | 365 days prior | Obesity | 6,711 | 6,711 | yes |
| first CKD | 82,138 | 365 days prior | Asthma | 11,796 | 11,796 | yes |
| first CKD | 82,138 | 365 days prior | Chronic kidney disease | 82,138 | 82,138 | yes |
| first CKD | 82,138 | 365 days prior | COPD | 2,546 | 2,546 | yes |
| first CKD | 82,138 | 90 days prior | Type 2 diabetes | 38,571 | 38,571 | yes |
| first CKD | 82,138 | 90 days prior | Heart failure | 179 | 179 | yes |
| first CKD | 82,138 | 90 days prior | Obesity | 2,808 | 2,808 | yes |
| first CKD | 82,138 | 90 days prior | Asthma | 4,931 | 4,931 | yes |
| first CKD | 82,138 | 90 days prior | Chronic kidney disease | 82,138 | 82,138 | yes |
| first CKD | 82,138 | 90 days prior | COPD | 1,047 | 1,047 | yes |
| first asthma | 83,639 | 365 days prior | Type 2 diabetes | 56,050 | 56,050 | yes |
| first asthma | 83,639 | 365 days prior | Heart failure | 315 | 315 | yes |
| first asthma | 83,639 | 365 days prior | Obesity | 6,734 | 6,734 | yes |
| first asthma | 83,639 | 365 days prior | Asthma | 83,639 | 83,639 | yes |
| first asthma | 83,639 | 365 days prior | Chronic kidney disease | 12,435 | 12,435 | yes |
| first asthma | 83,639 | 365 days prior | COPD | 15,379 | 15,379 | yes |
| first asthma | 83,639 | 90 days prior | Type 2 diabetes | 35,970 | 35,970 | yes |
| first asthma | 83,639 | 90 days prior | Heart failure | 133 | 133 | yes |
| first asthma | 83,639 | 90 days prior | Obesity | 3,036 | 3,036 | yes |
| first asthma | 83,639 | 90 days prior | Asthma | 83,639 | 83,639 | yes |
| first asthma | 83,639 | 90 days prior | Chronic kidney disease | 5,634 | 5,634 | yes |
| first asthma | 83,639 | 90 days prior | COPD | 15,379 | 15,379 | yes |

## Key observations

- FeatureExtraction 3.14.0 was run against the same Spark CDM over Hive JDBC.
- Analyses used `DomainConcept.sql` with explicit concept ids, `-365..0` and `-90..0`, `aggregated=TRUE`.
- Era-cache numerators are computed from the cached era table with the same window semantics.
- Every covariate numerator matches exactly; there is no tolerance.