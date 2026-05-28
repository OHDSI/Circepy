from typing import Optional

from sqlglot import exp as sge

from ..core import DateRange, NumericRange


def column_ref(table_alias: str, col: str) -> sge.Column:
    return sge.Column(this=col, table=table_alias)


def alias_expr(expr, alias: str) -> sge.Alias:
    return sge.Alias(this=expr, alias=sge.to_identifier(alias))


def date_add(unit: str, n, expr) -> sge.DateAdd:
    if isinstance(n, int):
        return sge.DateAdd(this=expr, expression=sge.Literal.number(n), unit=sge.Var(this=unit))
    return sge.DateAdd(this=expr, expression=n, unit=sge.Var(this=unit))


def coalesce(*exprs) -> sge.Coalesce | None:
    if not exprs:
        return None
    result = sge.Coalesce(this=exprs[0])
    result.args.setdefault("expressions", [])
    for e in exprs[1:]:
        result.args["expressions"].append(e)
    return result


def year_of(expr) -> sge.Year:
    return sge.Year(this=expr)


def datediff(unit: str, start, end) -> sge.DateDiff:
    start_ts = sge.TimeStrToTime(this=start) if isinstance(start, sge.Column) else start
    end_ts = sge.TimeStrToTime(this=end) if isinstance(end, sge.Column) else end
    return sge.DateDiff(this=end_ts, expression=start_ts, unit=sge.Var(this=unit))


def date_from_parts(year, month, day) -> sge.DateFromParts:
    return sge.DateFromParts(
        year=sge.Literal.number(year),
        month=sge.Literal.number(month),
        day=sge.Literal.number(day),
    )


def row_number_expr(partition_by: list, order_by: list) -> sge.Window:
    orders = [
        sge.Ordered(this=col, desc=False, nulls_first=True)
        if isinstance(col, sge.Column)
        else sge.Ordered(this=col, desc=False)
        for col in order_by
    ]
    order = sge.Order(expressions=orders)
    window = sge.Window(
        this=sge.RowNumber(),
        partition_by=partition_by,
        order=order,
    )
    return window


def codeset_join(
    codeset_table: str,
    concept_column: sge.Column,
    codeset_id: int,
    alias: str = "cs",
) -> sge.Join:
    return sge.Join(
        this=sge.Table(this=codeset_table, alias=alias),
        kind="INNER JOIN",
        on=sge.And(
            this=sge.EQ(this=concept_column, expression=column_ref(alias, "concept_id")),
            expression=sge.EQ(
                this=column_ref(alias, "codeset_id"),
                expression=sge.Literal.number(codeset_id),
            ),
        ),
    )


def codeset_in(column: sge.Column, codeset_id: int, exclude: bool = False) -> sge.In | sge.Not | None:
    subq = (
        sge.Select()
        .select(sge.column("concept_id"))
        .from_(sge.Table(this="#Codesets"))
        .where(
            sge.EQ(
                this=sge.column("codeset_id"),
                expression=sge.Literal.number(codeset_id),
            )
        )
    )
    result: sge.In = sge.In(this=column, expressions=[sge.Subquery(this=subq)])
    if exclude:
        return sge.Not(this=result)
    return result


def build_date_range_clause(
    column: sge.Column,
    date_range: Optional[DateRange],
) -> Optional[sge.Expression]:
    if date_range is None or date_range.op is None:
        return None
    op = date_range.op.lower()

    if op.endswith("bt"):
        negation = op.startswith("!")
        if date_range.value is None:
            return None
        lo = date_string_to_expr(date_range.value)
        hi = date_string_to_expr(date_range.extent) if date_range.extent else None
        if hi is None:
            return None
        result = sge.And(
            this=sge.GTE(this=column, expression=lo),
            expression=sge.LTE(this=column, expression=hi),
        )
        if negation:
            return sge.Not(this=result)
        return result

    if date_range.value is None:
        return None
    val = date_string_to_expr(date_range.value)
    sql_op = _get_sql_operator(op)
    if sql_op == "=":
        return sge.EQ(this=column, expression=val)
    elif sql_op == "<>":
        return sge.NEQ(this=column, expression=val)
    elif sql_op == ">":
        return sge.GT(this=column, expression=val)
    elif sql_op == ">=":
        return sge.GTE(this=column, expression=val)
    elif sql_op == "<":
        return sge.LT(this=column, expression=val)
    elif sql_op == "<=":
        return sge.LTE(this=column, expression=val)
    return None


def _get_sql_operator(op: str) -> str:
    operators = {
        "lt": "<",
        "lte": "<=",
        "eq": "=",
        "ne": "<>",
        "!eq": "<>",
        "gt": ">",
        "gte": ">=",
    }
    return operators.get(op, "=")


def date_string_to_expr(date_str: str) -> sge.DateFromParts:
    parts = date_str.split("-")
    year = int(parts[0])
    month = int(parts[1])
    day = int(parts[2])
    return date_from_parts(year, month, day)


def build_numeric_range_clause(
    column,
    numeric_range: Optional[NumericRange],
) -> Optional[sge.Expression]:
    if numeric_range is None or numeric_range.op is None:
        return None
    op = numeric_range.op.lower()

    if op.endswith("bt"):
        if numeric_range.value is None or numeric_range.extent is None:
            return None
        negation = op.startswith("!")
        lo = sge.Literal.number(int(numeric_range.value))
        hi = sge.Literal.number(int(numeric_range.extent))
        result = sge.And(
            this=sge.GTE(this=column, expression=lo), expression=sge.LTE(this=column, expression=hi)
        )
        if negation:
            return sge.Not(this=result)
        return result

    if numeric_range.value is None:
        return None
    val = sge.Literal.number(int(numeric_range.value))
    sql_op = _get_sql_operator(op)
    if sql_op == "=":
        return sge.EQ(this=column, expression=val)
    elif sql_op == "<>":
        return sge.NEQ(this=column, expression=val)
    elif sql_op == ">":
        return sge.GT(this=column, expression=val)
    elif sql_op == ">=":
        return sge.GTE(this=column, expression=val)
    elif sql_op == "<":
        return sge.LT(this=column, expression=val)
    elif sql_op == "<=":
        return sge.LTE(this=column, expression=val)
    return None


def build_text_filter_clause(
    column: sge.Column,
    text_filter,
) -> Optional[sge.Expression]:
    if text_filter is None:
        return None
    if isinstance(text_filter, str):
        return sge.Like(
            this=column,
            expression=sge.Literal.string(f"%{text_filter}%"),
        )
    text = getattr(text_filter, "text", None)
    op = getattr(text_filter, "op", "contains")
    if text is None:
        return None
    escaped = text.replace("'", "''")
    if op == "eq":
        return sge.EQ(this=column, expression=sge.Literal.string(escaped))
    elif op == "!eq":
        return sge.NEQ(this=column, expression=sge.Literal.string(escaped))
    elif op == "startsWith":
        return sge.Like(this=column, expression=sge.Literal.string(f"{escaped}%"))
    elif op == "endsWith":
        return sge.Like(this=column, expression=sge.Literal.string(f"%{escaped}"))
    elif op == "!contains":
        return sge.Not(this=sge.Like(this=column, expression=sge.Literal.string(f"%{escaped}%")))
    else:
        return sge.Like(this=column, expression=sge.Literal.string(f"%{escaped}%"))


def build_in_clause(column: sge.Column, values: list[int], exclude: bool = False) -> sge.In | sge.Not:
    sorted_vals = sorted(set(values))
    in_expr: sge.In = sge.In(
        this=column,
        expressions=[sge.Literal.number(v) for v in sorted_vals],
    )
    if exclude:
        return sge.Not(this=in_expr)
    return in_expr
