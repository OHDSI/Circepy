from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import ibis
import ibis.expr.operations as ops
from ibis.common.collections import FrozenOrderedDict

from .typing import IbisBackendLike, Table


def _is_nullish(value: Any) -> bool:
    if value is None:
        return True
    try:
        return value != value
    except Exception:
        return False


def _typed_literal(value: Any, *, dtype: str):
    if _is_nullish(value):
        return ibis.null().cast(dtype)
    return ibis.literal(value).cast(dtype)


def literal_column_relation(
    values: Iterable[Any],
    *,
    column_name: str,
    dtype: str,
    backend: IbisBackendLike | None = None,
) -> Table:
    """Build a 1-column relation from Python literals without `ibis.memtable(...)`."""
    _ = backend
    values_list = list(values)
    if not values_list:
        dummy = ops.DummyTable(
            values=FrozenOrderedDict({column_name: ibis.null().cast(dtype).op()})
        ).to_expr()
        return dummy.select(dummy[column_name]).filter(ibis.literal(False))

    array_type = f"array<{dtype}>"
    literal_array = ibis.literal(values_list, type=array_type)
    dummy = ops.DummyTable(values=FrozenOrderedDict({"__values__": literal_array.op()})).to_expr()
    unnested = ops.TableUnnest(
        dummy.op(),
        dummy["__values__"].op(),
        column_name,
        None,
        False,
    ).to_expr()
    return unnested.select(unnested[column_name])


def _single_row_relation(
    row: Mapping[str, Any],
    *,
    schema: Mapping[str, str],
) -> Table:
    return ops.DummyTable(
        values=FrozenOrderedDict(
            {column: _typed_literal(row.get(column), dtype=dtype).op() for column, dtype in schema.items()}
        )
    ).to_expr()


def literal_rows_relation(
    rows: Sequence[Mapping[str, Any]],
    *,
    schema: Mapping[str, str],
    backend: IbisBackendLike | None = None,
) -> Table:
    """Build a typed relation from row dictionaries without `ibis.memtable(...)`."""
    _ = backend
    if not schema:
        raise ValueError("literal_rows_relation requires a non-empty schema.")

    if not rows:
        empty_row = _single_row_relation(
            dict.fromkeys(schema),
            schema=schema,
        )
        return empty_row.filter(ibis.literal(False))

    relation: Table = _single_row_relation(rows[0], schema=schema)
    for row in rows[1:]:
        relation = relation.union(_single_row_relation(row, schema=schema), distinct=False)
    return relation


def table_from_literal_list(
    values: Iterable[int],
    *,
    column_name: str,
    element_type: str = "int64",
) -> Table:
    """Backward-compatible wrapper over `literal_column_relation`."""
    return literal_column_relation(values, column_name=column_name, dtype=element_type)


__all__ = ["literal_column_relation", "literal_rows_relation", "table_from_literal_list"]
