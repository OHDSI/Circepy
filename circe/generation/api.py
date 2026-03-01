from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from ..cohortdefinition import BuildExpressionQueryOptions, CohortExpression
from ..execution.api import build_cohort, write_relation
from ..execution.typing import IbisBackendLike
from .common import (
    effective_policy,
    project_to_cohort_relation,
    target_rows_relation,
    upsert_single_row,
)
from .config import (
    CohortSetDefinition,
    GenerationConfig,
    GenerationPolicy,
    GenerationTarget,
    NamedCohortExpression,
)
from .fingerprint import (
    DEFAULT_ENGINE_VERSION,
    fingerprint_expression,
    fingerprint_generation_request,
    fingerprint_options,
)
from .metadata import GenerationSetStatus, GenerationStatus
from .status import get_generated_cohort_status
from .tables import (
    COHORT_CHECKSUM_SCHEMA,
    COHORT_METADATA_SCHEMA,
    cohort_row_count,
    create_generation_tables,
    utc_now_iso,
)


def _target_to_named(target: GenerationTarget) -> NamedCohortExpression:
    return NamedCohortExpression(
        cohort_id=target.cohort_id,
        expression=target.expression,
        cohort_name=target.cohort_name,
        options=target.options,
    )


def generate_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cohort_id: int,
    cohort_name: str | None = None,
    config: GenerationConfig,
    policy: GenerationPolicy | None = None,
    options: BuildExpressionQueryOptions | None = None,
    data_version_token: str | None = None,
) -> GenerationStatus:
    create_generation_tables(backend, config)

    resolved_policy = effective_policy(config, policy)
    expression_hash = fingerprint_expression(expression)
    options_hash = fingerprint_options(options)
    combined_hash = fingerprint_generation_request(
        expression,
        options,
        engine_version=DEFAULT_ENGINE_VERSION,
        target_table=config.cohort_table,
        data_version_token=data_version_token,
    )

    previous = get_generated_cohort_status(
        backend,
        cohort_id=cohort_id,
        config=config,
    )
    previous_hash = previous.combined_hash

    has_existing = previous.status != "missing" or previous.row_count not in {None, 0}
    if resolved_policy == "fail" and has_existing:
        raise RuntimeError(
            f"Generation policy 'fail' blocked cohort_id={cohort_id}; existing rows or metadata found."
        )

    should_generate = True
    if resolved_policy == "skip_if_same" and previous_hash == combined_hash:
        should_generate = False
    if resolved_policy == "replace_if_changed" and previous_hash == combined_hash:
        should_generate = False

    generated_at = utc_now_iso()

    if not should_generate:
        status = GenerationStatus(
            cohort_id=int(cohort_id),
            cohort_name=cohort_name,
            policy=resolved_policy,
            status="skipped",
            target_table=config.cohort_table,
            results_schema=config.results_schema,
            row_count=cohort_row_count(backend, config=config, cohort_id=cohort_id),
            expression_hash=expression_hash,
            options_hash=options_hash,
            combined_hash=combined_hash,
            previous_combined_hash=previous_hash,
            generated_at=generated_at,
            message="Skipped because checksum matched existing generation.",
        )

        upsert_single_row(
            backend,
            table_name=config.metadata_table,
            schema=COHORT_METADATA_SCHEMA,
            database=config.results_schema,
            key_field="cohort_id",
            row={
                "cohort_id": int(cohort_id),
                "cohort_name": cohort_name,
                "target_table": config.cohort_table,
                "results_schema": config.results_schema,
                "expression_hash": expression_hash,
                "engine_version": DEFAULT_ENGINE_VERSION,
                "generated_at": generated_at,
                "is_subset": False,
                "parent_cohort_id": None,
                "subset_definition_id": None,
                "status": "skipped",
            },
        )
        return status

    relation = build_cohort(
        expression,
        backend=backend,
        cdm_schema=config.cdm_schema,
        results_schema=config.results_schema,
        options=options,
    )
    cohort_rows = project_to_cohort_relation(relation, cohort_id=cohort_id)

    final_rows = target_rows_relation(
        backend,
        config=config,
        cohort_id=cohort_id,
        new_rows=cohort_rows,
    )

    write_relation(
        final_rows,
        backend=backend,
        target_table=config.cohort_table,
        results_schema=config.results_schema,
        if_exists="replace",
        temporary=False,
    )

    written_row_count = cohort_row_count(backend, config=config, cohort_id=cohort_id)
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
            "cohort_id": int(cohort_id),
            "cohort_name": cohort_name,
            "target_table": config.cohort_table,
            "results_schema": config.results_schema,
            "expression_hash": expression_hash,
            "engine_version": DEFAULT_ENGINE_VERSION,
            "generated_at": generated_at,
            "is_subset": False,
            "parent_cohort_id": None,
            "subset_definition_id": None,
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
            "cohort_id": int(cohort_id),
            "expression_hash": expression_hash,
            "options_hash": options_hash,
            "combined_hash": combined_hash,
            "generated_at": generated_at,
        },
    )

    return GenerationStatus(
        cohort_id=int(cohort_id),
        cohort_name=cohort_name,
        policy=resolved_policy,
        status=outcome,
        target_table=config.cohort_table,
        results_schema=config.results_schema,
        row_count=written_row_count,
        expression_hash=expression_hash,
        options_hash=options_hash,
        combined_hash=combined_hash,
        previous_combined_hash=previous_hash,
        generated_at=generated_at,
        message=None,
    )


def _iter_named_targets(
    cohorts: Iterable[GenerationTarget | NamedCohortExpression] | CohortSetDefinition,
) -> list[NamedCohortExpression]:
    if isinstance(cohorts, CohortSetDefinition):
        return list(cohorts.cohorts)

    normalized: list[NamedCohortExpression] = []
    for cohort in cohorts:
        if isinstance(cohort, NamedCohortExpression):
            normalized.append(cohort)
        else:
            normalized.append(_target_to_named(cohort))
    return normalized


def generate_cohort_set(
    cohorts: Iterable[GenerationTarget | NamedCohortExpression] | CohortSetDefinition,
    *,
    backend: IbisBackendLike,
    config: GenerationConfig,
    policy: GenerationPolicy | None = None,
    options: BuildExpressionQueryOptions | None = None,
    cohort_ids: set[int] | None = None,
    cohort_names: set[str] | None = None,
    changed_only: bool = False,
    continue_on_error: bool = False,
    data_version_token: str | None = None,
) -> GenerationSetStatus:
    targets = _iter_named_targets(cohorts)

    statuses: list[GenerationStatus] = []
    for target in targets:
        if cohort_ids is not None and int(target.cohort_id) not in cohort_ids:
            continue
        if cohort_names is not None and target.cohort_name not in cohort_names:
            continue

        target_options = target.options if target.options is not None else options

        if changed_only:
            expression_hash = fingerprint_expression(target.expression)
            options_hash = fingerprint_options(target_options)
            combined_hash = fingerprint_generation_request(
                target.expression,
                target_options,
                engine_version=DEFAULT_ENGINE_VERSION,
                target_table=config.cohort_table,
                data_version_token=data_version_token,
            )
            current = get_generated_cohort_status(
                backend,
                cohort_id=target.cohort_id,
                config=config,
            )
            if current.combined_hash == combined_hash:
                statuses.append(
                    GenerationStatus(
                        cohort_id=int(target.cohort_id),
                        cohort_name=target.cohort_name,
                        policy=(policy or config.default_policy),
                        status="skipped",
                        target_table=config.cohort_table,
                        results_schema=config.results_schema,
                        row_count=current.row_count,
                        expression_hash=expression_hash,
                        options_hash=options_hash,
                        combined_hash=combined_hash,
                        previous_combined_hash=current.combined_hash,
                        generated_at=utc_now_iso(),
                        message="Skipped by changed_only mode.",
                    )
                )
                continue

        try:
            statuses.append(
                generate_cohort(
                    target.expression,
                    backend=backend,
                    cohort_id=target.cohort_id,
                    cohort_name=target.cohort_name,
                    config=config,
                    policy=policy,
                    options=target_options,
                    data_version_token=data_version_token,
                )
            )
        except Exception as exc:
            failed = GenerationStatus(
                cohort_id=int(target.cohort_id),
                cohort_name=target.cohort_name,
                policy=(policy or config.default_policy),
                status="failed",
                target_table=config.cohort_table,
                results_schema=config.results_schema,
                row_count=None,
                expression_hash=None,
                options_hash=None,
                combined_hash=None,
                previous_combined_hash=None,
                generated_at=utc_now_iso(),
                message=str(exc),
            )
            statuses.append(failed)
            if not continue_on_error:
                raise

    generated = sum(1 for s in statuses if s.status == "generated")
    replaced = sum(1 for s in statuses if s.status == "replaced")
    skipped = sum(1 for s in statuses if s.status == "skipped")
    failed = sum(1 for s in statuses if s.status == "failed")

    return GenerationSetStatus(
        total=len(statuses),
        generated=generated,
        replaced=replaced,
        skipped=skipped,
        failed=failed,
        statuses=tuple(statuses),
    )


__all__ = [
    "create_generation_tables",
    "generate_cohort",
    "generate_cohort_set",
    "get_generated_cohort_status",
]
