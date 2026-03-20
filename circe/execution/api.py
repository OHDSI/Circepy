from __future__ import annotations

from typing import Literal

from ..cohortdefinition import CohortExpression
from ..evaluation.models import EvaluationRubric, RubricSet
from .databricks_compat import maybe_apply_databricks_post_connect_workaround
from .engine.cohort import build_cohort_table
from .errors import ExecutionError
from .ibis.context import make_execution_context
from .ibis.materialize import project_to_ohdsi_cohort_table
from .ibis.operations import (
    cohort_rows_exist,
    create_table,
    exclude_cohort_rows,
    insert_relation,
    read_table,
    replace_cohort_rows_transactionally,
    supports_transactional_replace,
    table_exists,
)
from .normalize.cohort import normalize_cohort
from .typing import IbisBackendLike, Table


def build_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
) -> Table:
    """Normalize, compile, and assemble a cohort relation."""
    maybe_apply_databricks_post_connect_workaround(backend)

    normalized = normalize_cohort(expression)

    ctx = make_execution_context(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        concept_sets=normalized.concept_sets,
    )

    return build_cohort_table(normalized, ctx)


def write_relation(
    relation: Table,
    *,
    backend: IbisBackendLike,
    target_table: str,
    target_schema: str | None = None,
    if_exists: Literal["fail", "replace"] = "fail",
    temporary: bool = False,
) -> None:
    """Materialize a relation to a backend table."""
    if if_exists not in {"fail", "replace"}:
        raise ValueError("if_exists must be one of {'fail', 'replace'} for write_relation.")

    maybe_apply_databricks_post_connect_workaround(backend)

    write_kwargs = {
        "obj": relation,
        "overwrite": if_exists == "replace",
    }
    if temporary:
        write_kwargs["temp"] = True

    try:
        create_table(
            backend,
            table_name=target_table,
            schema=target_schema,
            **write_kwargs,
        )
    except Exception as exc:
        schema_label = target_schema if target_schema is not None else "<default>"
        raise ExecutionError(
            "Ibis executor write error: failed writing relation to "
            f"table '{target_table}' in schema '{schema_label}' "
            f"(if_exists={if_exists!r}, temporary={temporary})."
        ) from exc


def write_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    cohort_table: str,
    cohort_id: int,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    if_exists: Literal["fail", "replace"] = "fail",
) -> None:
    """Build cohort rows and materialize them with cohort-scoped semantics."""
    if if_exists not in {"fail", "replace"}:
        raise ValueError("if_exists must be one of {'fail', 'replace'} for write_cohort.")

    new_rows = build_cohort(
        expression,
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
    )
    new_rows = project_to_ohdsi_cohort_table(new_rows, cohort_id=cohort_id)

    if not table_exists(backend, table_name=cohort_table, schema=results_schema):
        write_relation(
            new_rows,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
            if_exists="fail",
        )
        return

    if if_exists == "fail":
        if cohort_rows_exist(
            backend,
            cohort_table=cohort_table,
            results_schema=results_schema,
            cohort_id=cohort_id,
        ):
            raise ExecutionError(
                "Ibis executor write error: cohort table "
                f"'{cohort_table}' already contains rows for cohort_id={cohort_id}."
            )
        insert_relation(
            new_rows,
            backend=backend,
            target_table=cohort_table,
            target_schema=results_schema,
        )
        return

    if supports_transactional_replace(backend):
        replace_cohort_rows_transactionally(
            new_rows,
            backend=backend,
            cohort_table=cohort_table,
            results_schema=results_schema,
            cohort_id=cohort_id,
        )
        return

    existing = read_table(
        backend,
        table_name=cohort_table,
        schema=results_schema,
    )
    filtered = exclude_cohort_rows(existing, cohort_id=cohort_id)
    relation = filtered.union(new_rows, distinct=False)
    write_relation(
        relation,
        backend=backend,
        target_table=cohort_table,
        target_schema=results_schema,
        if_exists="replace",
    )


def evaluate_cohort(
    rubric: EvaluationRubric,
    index_events: Table,
    *,
    ruleset_id: int,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    include_cohort_id: bool = True,
) -> Table:
    """Normalize, compile, and execute an evaluation rubric natively."""
    import ibis

    from .evaluation import build_evaluation

    maybe_apply_databricks_post_connect_workaround(backend)

    mapped_events = index_events
    col_map = {}
    if "subject_id" in index_events.columns and "person_id" not in index_events.columns:
        col_map["person_id"] = "subject_id"
    if "cohort_start_date" in index_events.columns and "start_date" not in index_events.columns:
        col_map["start_date"] = "cohort_start_date"
    if "cohort_end_date" in index_events.columns and "end_date" not in index_events.columns:
        col_map["end_date"] = "cohort_end_date"

    if col_map:
        mapped_events = mapped_events.rename(col_map)

    if "event_id" not in mapped_events.columns:
        mapped_events = mapped_events.mutate(event_id=ibis.literal(0, type="int64"))

    from .normalize.cohort import _extract_codesets

    ctx = make_execution_context(
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        concept_sets=_extract_codesets(rubric.concept_sets),
    )

    return build_evaluation(
        rubric=rubric,
        index_events=mapped_events,
        ctx=ctx,
        ruleset_id=ruleset_id,
        include_cohort_id=include_cohort_id,
    )


def write_evaluation(
    rubric: EvaluationRubric,
    index_events: Table,
    *,
    ruleset_id: int,
    backend: IbisBackendLike,
    cdm_schema: str,
    target_table: str = "cohort_rubric",
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
    include_cohort_id: bool = True,
    if_exists: Literal["fail", "replace"] = "fail",
) -> None:
    """Build evaluation rows and materialize them."""
    import ibis

    if if_exists not in {"fail", "replace"}:
        raise ValueError("if_exists must be one of {'fail', 'replace'} for write_evaluation.")

    new_rows = evaluate_cohort(
        rubric,
        index_events,
        ruleset_id=ruleset_id,
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        include_cohort_id=include_cohort_id,
    )

    if not table_exists(backend, table_name=target_table, schema=results_schema):
        write_relation(
            new_rows,
            backend=backend,
            target_table=target_table,
            target_schema=results_schema,
            if_exists="fail",
        )
        return

    existing = read_table(backend, table_name=target_table, schema=results_schema)
    ruleset_id_expr = ibis.literal(int(ruleset_id), type="int64")

    has_rows = (
        len(existing.filter(existing.ruleset_id.cast("int64") == ruleset_id_expr).limit(1).execute()) > 0
    )

    if if_exists == "fail" and has_rows:
        raise ExecutionError(
            f"Ibis executor write error: target table '{target_table}' already contains rows for ruleset_id={ruleset_id}."
        )

    filtered = existing.filter(existing.ruleset_id.cast("int64") != ruleset_id_expr)
    relation = filtered.union(new_rows, distinct=False)

    write_relation(
        relation,
        backend=backend,
        target_table=target_table,
        target_schema=results_schema,
        if_exists="replace",
    )


def calculate_cohort_metrics(
    rubric_set: RubricSet,
    index_events: Table,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
) -> Table:
    """Calculate Positive Predictive Value (PPV) and Sensitivity estimates for a target cohort."""
    from .metrics import calculate_cohort_metrics as _calculate_metrics

    return _calculate_metrics(
        rubric_set,
        index_events,
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
    )
