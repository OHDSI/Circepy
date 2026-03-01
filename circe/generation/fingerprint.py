from __future__ import annotations

import hashlib
import json
from typing import Any

from ..cohortdefinition import BuildExpressionQueryOptions, CohortExpression
from .subsets.definitions import SubsetDefinition, serialize_subset_definition

GENERATION_SCHEMA_VERSION = "generation-v1"
DEFAULT_ENGINE_VERSION = "execution-v1"


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def fingerprint_expression(expression: CohortExpression) -> str:
    payload = expression.model_dump(by_alias=True, exclude_none=False)
    return stable_hash(payload)


def fingerprint_options(options: BuildExpressionQueryOptions | None) -> str:
    if options is None:
        payload = {}
    else:
        payload = {
            "cdm_schema": options.cdm_schema,
            "target_table": options.target_table,
            "result_schema": options.result_schema,
            "vocabulary_schema": options.vocabulary_schema,
            "cohort_id": options.cohort_id,
            "cohort_id_field_name": options.cohort_id_field_name,
            "generate_stats": options.generate_stats,
        }
    return stable_hash(payload)


def fingerprint_generation_request(
    expression: CohortExpression,
    options: BuildExpressionQueryOptions | None,
    engine_version: str = DEFAULT_ENGINE_VERSION,
    target_table: str = "cohort",
    subset_context: dict[str, Any] | None = None,
    data_version_token: str | None = None,
) -> str:
    payload = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "engine_version": engine_version,
        "target_table": target_table,
        "expression_hash": fingerprint_expression(expression),
        "options_hash": fingerprint_options(options),
        "subset_context": subset_context or {},
    }
    if data_version_token is not None:
        payload["data_version_token"] = str(data_version_token)
    return stable_hash(payload)


def fingerprint_subset_definition(definition: SubsetDefinition) -> str:
    return stable_hash(serialize_subset_definition(definition))


def fingerprint_subset_generation_request(
    definition: SubsetDefinition,
    *,
    dependency_hash: str,
    engine_version: str = DEFAULT_ENGINE_VERSION,
    target_table: str = "cohort",
    data_version_token: str | None = None,
) -> str:
    payload = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "engine_version": engine_version,
        "target_table": target_table,
        "subset_definition_hash": fingerprint_subset_definition(definition),
        "dependency_hash": dependency_hash,
    }
    if data_version_token is not None:
        payload["data_version_token"] = str(data_version_token)
    return stable_hash(payload)
