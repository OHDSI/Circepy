from __future__ import annotations

import json

from ...execution.api import write_relation
from ...execution.typing import IbisBackendLike, Table
from ..common import effective_policy, target_rows_relation, upsert_single_row
from ..config import GenerationConfig, GenerationPolicy
from ..fingerprint import (
    DEFAULT_ENGINE_VERSION,
    fingerprint_subset_definition,
    fingerprint_subset_generation_request,
)
from ..metadata import GenerationStatus
from ..status import get_generated_cohort_status
from ..tables import (
    COHORT_CHECKSUM_SCHEMA,
    COHORT_METADATA_SCHEMA,
    SUBSET_METADATA_SCHEMA,
    cohort_row_count,
    create_generation_tables,
    utc_now_iso,
)
from .compiler import apply_subset as compile_subset
from .definitions import SubsetDefinition
from .metadata import resolve_generation_dependencies


def _resolve_subset_definition_id(definition: SubsetDefinition) -> str:
    if definition.subset_definition_id is not None:
        return definition.subset_definition_id
    return fingerprint_subset_definition(definition)


def _parent_relation(
    backend: IbisBackendLike,
    *,
    definition: SubsetDefinition,
    config: GenerationConfig,
) -> Table:
    cohort_table = backend.table(config.cohort_table, database=config.results_schema)
    return cohort_table.filter(
        cohort_table.cohort_definition_id == int(definition.parent_cohort_id)
    ).select(
        "cohort_definition_id",
        "subject_id",
        "cohort_start_date",
        "cohort_end_date",
    )


def apply_subset(
    relation: Table,
    *,
    backend: IbisBackendLike,
    config: GenerationConfig,
    definition: SubsetDefinition,
) -> Table:
    """Apply a subset definition to a cohort relation and return transformed rows."""
    return compile_subset(
        relation,
        backend=backend,
        config=config,
        definition=definition,
    )


def generate_subset(
    definition: SubsetDefinition,
    *,
    backend: IbisBackendLike,
    generated_cohort_id: int,
    config: GenerationConfig,
    policy: GenerationPolicy | None = None,
    data_version_token: str | None = None,
) -> GenerationStatus:
    """Generate and persist a subset cohort with dependency-aware checksums."""
    create_generation_tables(backend, config)

    subset_definition_id = _resolve_subset_definition_id(definition)
    operator_sequence_hash = fingerprint_subset_definition(definition)
    dependencies = resolve_generation_dependencies(
        backend,
        definition=definition,
        config=config,
    )
    dependency_hash = dependencies["dependency_hash"]
    combined_hash = fingerprint_subset_generation_request(
        definition,
        dependency_hash=dependency_hash,
        engine_version=DEFAULT_ENGINE_VERSION,
        target_table=config.cohort_table,
        data_version_token=data_version_token,
    )

    resolved_policy = effective_policy(config, policy)
    previous = get_generated_cohort_status(
        backend,
        cohort_id=generated_cohort_id,
        config=config,
    )
    previous_hash = previous.combined_hash

    has_existing = previous.status != "missing" or previous.row_count not in {None, 0}
    if resolved_policy == "fail" and has_existing:
        raise RuntimeError(
            "Generation policy 'fail' blocked subset cohort_id="
            f"{generated_cohort_id}; existing rows or metadata found."
        )

    should_generate = True
    if resolved_policy in {"skip_if_same", "replace_if_changed"} and previous_hash == combined_hash:
        should_generate = False

    generated_at = utc_now_iso()

    if not should_generate:
        upsert_single_row(
            backend,
            table_name=config.metadata_table,
            schema=COHORT_METADATA_SCHEMA,
            database=config.results_schema,
            key_field="cohort_id",
            row={
                "cohort_id": int(generated_cohort_id),
                "cohort_name": definition.subset_name,
                "target_table": config.cohort_table,
                "results_schema": config.results_schema,
                "expression_hash": operator_sequence_hash,
                "engine_version": DEFAULT_ENGINE_VERSION,
                "generated_at": generated_at,
                "is_subset": True,
                "parent_cohort_id": int(definition.parent_cohort_id),
                "subset_definition_id": subset_definition_id,
                "status": "skipped",
            },
        )

        return GenerationStatus(
            cohort_id=int(generated_cohort_id),
            cohort_name=definition.subset_name,
            policy=resolved_policy,
            status="skipped",
            target_table=config.cohort_table,
            results_schema=config.results_schema,
            row_count=cohort_row_count(
                backend,
                config=config,
                cohort_id=generated_cohort_id,
            ),
            expression_hash=operator_sequence_hash,
            options_hash=dependency_hash,
            combined_hash=combined_hash,
            previous_combined_hash=previous_hash,
            generated_at=generated_at,
            message="Skipped because checksum matched existing generation.",
        )

    parent_rows = _parent_relation(
        backend,
        definition=definition,
        config=config,
    )
    transformed = compile_subset(
        parent_rows,
        backend=backend,
        config=config,
        definition=definition,
    )
    subset_rows = transformed.select(
        transformed.cohort_definition_id.cast("int64").name("cohort_definition_id"),
        transformed.subject_id.cast("int64").name("subject_id"),
        transformed.cohort_start_date.cast("date").name("cohort_start_date"),
        transformed.cohort_end_date.cast("date").name("cohort_end_date"),
    ).mutate(cohort_definition_id=int(generated_cohort_id))

    final_rows = target_rows_relation(
        backend,
        config=config,
        cohort_id=generated_cohort_id,
        new_rows=subset_rows,
    )
    write_relation(
        final_rows,
        backend=backend,
        target_table=config.cohort_table,
        results_schema=config.results_schema,
        if_exists="replace",
        temporary=False,
    )

    written_row_count = cohort_row_count(
        backend,
        config=config,
        cohort_id=generated_cohort_id,
    )
    outcome = "generated"
    if has_existing and resolved_policy in {"replace", "replace_if_changed"}:
        outcome = "replaced"

    upsert_single_row(
        backend,
        table_name=config.metadata_table,
        schema=COHORT_METADATA_SCHEMA,
        database=config.results_schema,
        key_field="cohort_id",
        row={
            "cohort_id": int(generated_cohort_id),
            "cohort_name": definition.subset_name,
            "target_table": config.cohort_table,
            "results_schema": config.results_schema,
            "expression_hash": operator_sequence_hash,
            "engine_version": DEFAULT_ENGINE_VERSION,
            "generated_at": generated_at,
            "is_subset": True,
            "parent_cohort_id": int(definition.parent_cohort_id),
            "subset_definition_id": subset_definition_id,
            "status": outcome,
        },
    )
    upsert_single_row(
        backend,
        table_name=config.checksum_table,
        schema=COHORT_CHECKSUM_SCHEMA,
        database=config.results_schema,
        key_field="cohort_id",
        row={
            "cohort_id": int(generated_cohort_id),
            "expression_hash": operator_sequence_hash,
            "options_hash": dependency_hash,
            "combined_hash": combined_hash,
            "generated_at": generated_at,
        },
    )
    upsert_single_row(
        backend,
        table_name=config.subset_metadata_table,
        schema=SUBSET_METADATA_SCHEMA,
        database=config.results_schema,
        key_field="subset_definition_id",
        row={
            "subset_definition_id": subset_definition_id,
            "subset_name": definition.subset_name,
            "parent_cohort_id": int(definition.parent_cohort_id),
            "operator_sequence_hash": operator_sequence_hash,
            "generated_cohort_id": int(generated_cohort_id),
            "dependency_hash": dependency_hash,
            "dependency_payload": json.dumps(
                dependencies["payload"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ),
            "generated_at": generated_at,
        },
    )

    return GenerationStatus(
        cohort_id=int(generated_cohort_id),
        cohort_name=definition.subset_name,
        policy=resolved_policy,
        status=outcome,
        target_table=config.cohort_table,
        results_schema=config.results_schema,
        row_count=written_row_count,
        expression_hash=operator_sequence_hash,
        options_hash=dependency_hash,
        combined_hash=combined_hash,
        previous_combined_hash=previous_hash,
        generated_at=generated_at,
        message=None,
    )


__all__ = ["apply_subset", "generate_subset"]
