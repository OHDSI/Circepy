from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Tuple, Union

from .errors import ExecutionError
from .ibis.materialize import project_to_ohdsi_cohort_table
from .ibis.operations import table_exists

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl

    from ..cohortdefinition import CohortExpression


SchemaName = Union[str, Tuple[str, str]]
ExpressionInput = Union["CohortExpression", Mapping[str, Any], str, Path]


@dataclass(frozen=True)
class ExecutionOptions:
    """Legacy execution options preserved as compatibility wrappers."""

    cdm_schema: SchemaName | None = None
    vocabulary_schema: SchemaName | None = None
    result_schema: SchemaName | None = None

    cohort_id: int | None = None

    materialize_stages: bool = False
    materialize_codesets: bool = True
    temp_emulation_schema: SchemaName | None = None

    capture_sql: bool = False
    profile_dir: str | None = None


def schema_to_str(schema: SchemaName | None) -> str | None:
    """Normalize schema names to a string representation."""
    if schema is None:
        return None
    if isinstance(schema, tuple):
        return ".".join(schema)
    return schema


class IbisExecutor:
    """Legacy object API preserved as a thin wrapper over the new executor."""

    def __init__(self, conn: Any, options: ExecutionOptions | None = None):
        self._conn = conn
        self._options = options or ExecutionOptions()

    @property
    def conn(self) -> Any:
        return self._conn

    @property
    def options(self) -> ExecutionOptions:
        return self._options

    def build(self, expression: ExpressionInput) -> Any:
        from ..io import load_expression
        from .api import build_cohort as _build_cohort

        cohort_expression = load_expression(expression)
        return _build_cohort(
            cohort_expression,
            backend=self._conn,
            cdm_schema=schema_to_str(self._options.cdm_schema),
            vocabulary_schema=schema_to_str(self._options.vocabulary_schema),
            results_schema=schema_to_str(self._options.result_schema),
        )

    def to_polars(self, expression: ExpressionInput) -> pl.DataFrame:
        table = self.build(expression)
        if not hasattr(table, "to_polars"):
            raise RuntimeError("The returned ibis table does not support to_polars() on this backend.")
        return table.to_polars()

    def to_pandas(self, expression: ExpressionInput) -> pd.DataFrame:
        table = self.build(expression)
        if not hasattr(table, "to_pandas"):
            raise RuntimeError("The returned ibis table does not support to_pandas() on this backend.")
        return table.to_pandas()

    def write(
        self,
        expression: ExpressionInput,
        *,
        table: str,
        schema: SchemaName | None = None,
        overwrite: bool = True,
        append: bool = False,
        cohort_id: int | None = None,
    ) -> Any:
        from ..io import load_expression
        from .api import build_cohort as _build_cohort
        from .api import write_relation as _write_relation

        if append and overwrite:
            raise ValueError("`append=True` and `overwrite=True` cannot be used together.")

        effective_cohort_id = cohort_id if cohort_id is not None else self._options.cohort_id
        if effective_cohort_id is None:
            raise ExecutionError(
                "Ibis executor write error: cohort_id is required when writing OHDSI cohort-table rows."
            )
        target_schema = schema_to_str(schema) or schema_to_str(self._options.result_schema)
        relation = _build_cohort(
            load_expression(expression),
            backend=self._conn,
            cdm_schema=schema_to_str(self._options.cdm_schema),
            vocabulary_schema=schema_to_str(self._options.vocabulary_schema),
            results_schema=target_schema,
        )
        relation = project_to_ohdsi_cohort_table(
            relation,
            cohort_id=effective_cohort_id,
        )

        if append and table_exists(self._conn, table_name=table, schema=target_schema):
            try:
                if target_schema is not None:
                    existing = self._conn.table(table, database=target_schema)
                else:
                    existing = self._conn.table(table)
                relation = existing.union(relation, distinct=False)
            except Exception as exc:
                raise ExecutionError(
                    f"Ibis executor write error: failed reading existing table '{table}' for append."
                ) from exc

        _write_relation(
            relation,
            backend=self._conn,
            target_table=table,
            target_schema=target_schema,
            if_exists="replace" if overwrite or append else "fail",
            temporary=False,
        )

        try:
            if target_schema is not None:
                return self._conn.table(table, database=target_schema)
            return self._conn.table(table)
        except Exception as exc:
            raise ExecutionError(f"Ibis executor write error: failed to read back table '{table}'.") from exc

    def captured_sql(self) -> list[tuple[str, str]]:
        return []

    def close(self) -> None:
        return None

    def __enter__(self) -> IbisExecutor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def build_ibis(
    expression: ExpressionInput,
    conn: Any,
    options: ExecutionOptions | None = None,
) -> Any:
    with IbisExecutor(conn, options) as executor:
        return executor.build(expression)


def to_polars(
    expression: ExpressionInput,
    conn: Any,
    options: ExecutionOptions | None = None,
) -> pl.DataFrame:
    with IbisExecutor(conn, options) as executor:
        return executor.to_polars(expression)


def write_cohort(
    expression: ExpressionInput,
    conn: Any,
    *,
    table: str,
    schema: SchemaName | None = None,
    overwrite: bool = True,
    append: bool = False,
    cohort_id: int | None = None,
    options: ExecutionOptions | None = None,
) -> Any:
    with IbisExecutor(conn, options) as executor:
        return executor.write(
            expression,
            table=table,
            schema=schema,
            overwrite=overwrite,
            append=append,
            cohort_id=cohort_id,
        )
