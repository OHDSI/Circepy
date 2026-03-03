from __future__ import annotations

from typing import Iterable

import ibis
import ibis.expr.operations as ops
import ibis.expr.types as ir
from ibis.common.collections import FrozenOrderedDict


def table_from_literal_list(
    values: Iterable[int],
    *,
    column_name: str,
    element_type: str = "int64",
) -> ir.Table:
    """
    Build a 1-column table from a Python list without using `ibis.memtable`.

    This avoids Databricks' memtable upload machinery (which depends on a writable
    Unity Catalog volume) while still producing a pure Ibis expression.
    """
    values_list = list(values)
    if not values_list:
        dummy = ops.DummyTable(
            values=FrozenOrderedDict({column_name: ibis.null().cast(element_type).op()})
        ).to_expr()
        return dummy.select(dummy[column_name]).filter(ibis.literal(False))

    array_type = f"array<{element_type}>"
    arr = ibis.literal(values_list, type=array_type)

    dummy = ops.DummyTable(values=FrozenOrderedDict({"__values__": arr.op()})).to_expr()
    unnested = ops.TableUnnest(
        dummy.op(),
        dummy["__values__"].op(),
        column_name,
        None,
        False,
    ).to_expr()
    return unnested.select(unnested[column_name])
