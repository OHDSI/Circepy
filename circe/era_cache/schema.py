"""Table names and column contracts for the era cache."""

from __future__ import annotations

__all__ = [
    "CACHE_TABLES",
    "LARGE_TABLES",
    "CATEGORICAL_TABLE",
    "CATEGORICAL_COLUMNS",
    "CONTINUOUS_COLUMNS",
    "CONTINUOUS_TABLE",
    "PRESENCE_COLUMNS",
    "PRESENCE_TABLE",
    "REGISTRY_COLUMNS",
    "REGISTRY_TABLE",
]

PRESENCE_TABLE = "era_feature_presence"
CONTINUOUS_TABLE = "era_feature_continuous"
REGISTRY_TABLE = "era_feature_registry"

PRESENCE_COLUMNS = {
    "feature_key": "string",
    "subject_id": "int64",
    "era_start": "date",
    "era_end": "date",
    "concept_id": "int64",
}

# Continuous features carry the observed number and the reference range.
# "Above normal range" is computed at read time, never stored.
CONTINUOUS_COLUMNS = {
    **PRESENCE_COLUMNS,
    "value_num": "float64",
    "unit_concept_id": "int64",
    "range_low": "float64",
    "range_high": "float64",
    "operator_concept_id": "int64",
}

# Categorical features carry an observed OMOP concept as the result.
CATEGORICAL_COLUMNS = {
    **PRESENCE_COLUMNS,
    "value_concept_id": "int64",
    "unit_concept_id": "int64",
}

# Categorical features live beside continuous value features; a categorical
# result is an observed OMOP concept, never a number.
CATEGORICAL_TABLE = "era_feature_categorical"

REGISTRY_COLUMNS = {
    "feature_key": "string",
    "cache_key": "string",
    "family": "string",
    "feature_class": "string",
    "table_name": "string",
    "completed": "boolean",
    "row_count": "int64",
    "subject_count": "int64",
    "cdm_fingerprint": "string",
    "vocab_fingerprint": "string",
    "engine_fingerprint": "string",
    "updated_at": "timestamp",
    "completed_at": "timestamp",
}

# Tables that can grow to millions of rows; readers should avoid broadcasting.
LARGE_TABLES = (PRESENCE_TABLE, CATEGORICAL_TABLE, CONTINUOUS_TABLE)

CACHE_TABLES = {
    "presence": PRESENCE_TABLE,
    "categorical": CATEGORICAL_TABLE,
    "continuous": CONTINUOUS_TABLE,
    "registry": REGISTRY_TABLE,
}
