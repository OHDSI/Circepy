"""Render and execute legacy CohortGenerator SQL as a cohort-row oracle.

The loader stores the pre-generated SQL from the legacy ``sql/`` folder.  These
helpers render its ``@parameter`` placeholders, translate it from SQL Server to
the target dialect, and compare the rows it produces with circepy's own
execution.  This is the practical proof that the Python engine (including the
shared-checkpoint path) produces the same cohorts as the R/Java toolchain.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from ..sqlrender import render, split_sql, translate
from ._core import CohortDefinitionSet
from ._legacy import LegacyCohortSetError, LoadedCohortDefinition

logger = logging.getLogger(__name__)

__all__ = [
    "LegacySqlComparison",
    "render_legacy_sql",
    "verify_against_legacy_sql",
]


@dataclass(frozen=True)
class LegacySqlComparison:
    """Row-count and equality result for one cohort."""

    cohort_id: int
    cohort_name: str
    legacy_rows: int
    generated_rows: int
    matching_rows: bool


_RESULT_TABLE_DDL = {
    "cohort_inclusion_result": (
        "cohort_definition_id BIGINT, inclusion_rule_mask BIGINT, person_count BIGINT, mode_id BIGINT"
    ),
    "cohort_inclusion_stats": (
        "cohort_definition_id BIGINT, rule_sequence BIGINT, person_count BIGINT, "
        "gain_count BIGINT, person_total BIGINT, mode_id BIGINT"
    ),
    "cohort_summary_stats": "cohort_definition_id BIGINT, base_count BIGINT, final_count BIGINT, mode_id BIGINT",
    "cohort_censor_stats": "cohort_definition_id BIGINT",
}


def _qualified(schema: str | None, table: str) -> str:
    if schema:
        return f"{schema}.{table}"
    return table


def _render_sql(
    definition: LoadedCohortDefinition,
    *,
    cdm_schema: str,
    vocabulary_schema: str,
    results_schema: str | None,
    target_schema: str | None,
    target_table: str,
    target_cohort_id: int,
    target_dialect: str,
    session_id: str | None,
    temp_emulation_schema: str | None,
) -> str:
    if not definition.sql:
        raise LegacyCohortSetError(
            f"Cohort {definition.cohort_id} ({definition.cohort_name}) has no legacy SQL to render"
        )

    rendered = render(
        definition.sql,
        cdm_database_schema=cdm_schema,
        vocabulary_database_schema=vocabulary_schema,
        results_database_schema=results_schema or cdm_schema,
        target_database_schema=target_schema or cdm_schema,
        target_cohort_table=target_table,
        target_cohort_id=int(target_cohort_id),
    )
    return translate(
        rendered,
        target_dialect=target_dialect,
        session_id=session_id,
        temp_emulation_schema=temp_emulation_schema,
    )


def render_legacy_sql(
    definition: LoadedCohortDefinition,
    *,
    cdm_schema: str,
    vocabulary_schema: str | None = None,
    results_schema: str | None = None,
    target_schema: str | None = None,
    target_table: str,
    target_cohort_id: int | None = None,
    target_dialect: str = "duckdb",
    session_id: str | None = None,
    temp_emulation_schema: str | None = None,
) -> str:
    """Render and translate a loaded legacy SQL definition.

    Args:
        definition: A definition from :func:`load_cohort_definition_set`.
        cdm_schema: Schema for the CDM tables.
        vocabulary_schema: Schema for vocabulary tables (defaults to *cdm_schema*).
        results_schema: Schema for result/statistics tables (defaults to *cdm_schema*).
        target_schema: Schema for the target cohort table (defaults to *results_schema*).
        target_table: Target cohort table name.
        target_cohort_id: Cohort id value; defaults to ``definition.cohort_id``.
        target_dialect: ``circe.sqlrender`` target dialect, e.g. duckdb/postgresql/spark.
        session_id: Optional SqlRender session id for temporary-table translation.
        temp_emulation_schema: Optional schema for Oracle temporary-table emulation.

    Returns:
        The rendered, dialect-translated SQL string.
    """
    return _render_sql(
        definition,
        cdm_schema=cdm_schema,
        vocabulary_schema=vocabulary_schema or cdm_schema,
        results_schema=results_schema,
        target_schema=target_schema,
        target_table=target_table,
        target_cohort_id=int(definition.cohort_id if target_cohort_id is None else target_cohort_id),
        target_dialect=target_dialect,
        session_id=session_id,
        temp_emulation_schema=temp_emulation_schema,
    )


def _create_oracle_tables(
    backend: Any,
    *,
    target_schema: str | None,
    target_table: str,
    results_schema: str | None,
) -> None:
    target = _qualified(target_schema, target_table)
    backend.raw_sql(
        f"CREATE TABLE IF NOT EXISTS {target} ("
        "cohort_definition_id BIGINT, subject_id BIGINT, "
        "cohort_start_date DATE, cohort_end_date DATE)"
    )
    results = results_schema or target_schema
    for name, columns in _RESULT_TABLE_DDL.items():
        backend.raw_sql(f"CREATE TABLE IF NOT EXISTS {_qualified(results, name)} ({columns})")


def _drop_tables(backend: Any, schema: str | None, names: list[str]) -> None:
    for name in names:
        try:
            backend.drop_table(name, database=schema, force=True)
        except Exception:  # pragma: no cover - best effort in test/oracle tooling
            logger.debug("Could not drop %s.%s", schema, name, exc_info=True)


def verify_against_legacy_sql(
    cohort_set: CohortDefinitionSet,
    *,
    backend: Any,
    cdm_schema: str,
    vocabulary_schema: str | None = None,
    results_schema: str | None = None,
    target_schema: str | None = None,
    target_table: str = "cohort_legacy",
    generated_table: str = "cohort_circe",
    target_dialect: str = "duckdb",
    session_id: str | None = None,
    temp_emulation_schema: str | None = None,
    shared: bool = True,
    cleanup: bool = False,
) -> list[LegacySqlComparison]:
    """Execute legacy SQL and compare its cohort rows with circepy's output.

    The caller supplies a database connection with the CDM/vocabulary data and
    writable result schemas.  The function creates a legacy target table and a
    generated cohort table, runs every cohort with SQL, and compares rows with
    two-way ``EXCEPT``/``EXCEPT ALL``.

    This is intended for tests/benchmarks, not production cohort generation.
    It needs the legacy SQL's statistics tables, which are created if absent.
    """
    from ._generate import generate_cohort_set

    definitions = [definition for definition in cohort_set if isinstance(definition, LoadedCohortDefinition)]
    if len(definitions) != len(cohort_set):
        raise LegacyCohortSetError(
            "verify_against_legacy_sql requires a set loaded with load_cohort_definition_set()"
        )
    missing = [definition.cohort_id for definition in definitions if not definition.sql]
    if missing:
        raise LegacyCohortSetError(f"Cannot compare cohorts without SQL: {missing}")

    target_schema = target_schema or results_schema or cdm_schema
    results_schema = results_schema or target_schema
    target_dialect = target_dialect.lower()
    session_id = session_id or uuid.uuid4().hex[:8]
    if not session_id[0].isalpha():
        session_id = "c" + session_id[1:]

    _create_oracle_tables(
        backend,
        target_schema=target_schema,
        target_table=target_table,
        results_schema=results_schema,
    )

    for definition in definitions:
        sql = render_legacy_sql(
            definition,
            cdm_schema=cdm_schema,
            vocabulary_schema=vocabulary_schema or cdm_schema,
            results_schema=results_schema,
            target_schema=target_schema,
            target_table=target_table,
            target_cohort_id=definition.cohort_id,
            target_dialect=target_dialect,
            session_id=session_id,
            temp_emulation_schema=temp_emulation_schema,
        )
        for statement in split_sql(sql):
            if statement.strip():
                backend.raw_sql(statement)

    generate_cohort_set(
        cohort_set,
        backend=backend,
        cdm_schema=cdm_schema,
        vocabulary_schema=vocabulary_schema,
        results_schema=target_schema,
        cohort_table=generated_table,
        shared=shared,
    )

    legacy = _qualified(target_schema, target_table)
    generated = _qualified(target_schema, generated_table)
    comparisons: list[LegacySqlComparison] = []
    for definition in definitions:
        cohort_id = int(definition.cohort_id)
        columns = (
            "subject_id, CAST(cohort_start_date AS DATE) AS cohort_start_date, "
            "CAST(cohort_end_date AS DATE) AS cohort_end_date"
        )
        difference_sql = f"""
        SELECT COUNT(*) FROM (
          (SELECT {columns} FROM {legacy} WHERE cohort_definition_id = {cohort_id}
           EXCEPT ALL
           SELECT {columns} FROM {generated} WHERE cohort_definition_id = {cohort_id})
          UNION ALL
          (SELECT {columns} FROM {generated} WHERE cohort_definition_id = {cohort_id}
           EXCEPT ALL
           SELECT {columns} FROM {legacy} WHERE cohort_definition_id = {cohort_id})
        ) difference
        """
        difference = int(backend.raw_sql(difference_sql).fetchone()[0])
        legacy_rows = int(
            backend.raw_sql(
                f"SELECT COUNT(*) FROM {legacy} WHERE cohort_definition_id = {cohort_id}"
            ).fetchone()[0]
        )
        generated_rows = int(
            backend.raw_sql(
                f"SELECT COUNT(*) FROM {generated} WHERE cohort_definition_id = {cohort_id}"
            ).fetchone()[0]
        )
        comparisons.append(
            LegacySqlComparison(
                cohort_id=cohort_id,
                cohort_name=definition.cohort_name,
                legacy_rows=legacy_rows,
                generated_rows=generated_rows,
                matching_rows=difference == 0,
            )
        )

    if cleanup:
        _drop_tables(backend, target_schema, [target_table, generated_table])
        _drop_tables(backend, results_schema, list(_RESULT_TABLE_DDL))

    return comparisons
