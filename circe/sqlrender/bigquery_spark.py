from __future__ import annotations

import re
from enum import Enum

from .tokenizer import tokenize_sql
from .translator import _MatchedPattern, parse_search_pattern, search


class _ListType(Enum):
    SELECT = "SELECT"
    GROUP_BY = "GROUP_BY"
    ORDER_BY = "ORDER_BY"
    WITH_COLUMNS = "WITH_COLUMNS"
    IN = "IN"


class _CommaListIterator:
    """Iterates elements of a comma-separated list of expressions."""

    def __init__(self, expression_list: str, list_type: _ListType) -> None:
        self._list_type = list_type
        self._expression_list = expression_list
        self._list_prefix = ""
        self._list_suffix = ""
        self._expression_prefix = ""
        self._expression_suffix = ""
        self._current_match: _MatchedPattern | None = None

        self._split_list()
        self._expression_list = "," + self._expression_list + ","
        self._list_element_pattern = parse_search_pattern(", @@a ,")
        self._current_match = search(self._expression_list, self._list_element_pattern, 0)
        if self._current_match.start != -1:
            self._split_expression()

    def is_done(self) -> bool:
        return self._current_match is None or self._current_match.start == -1

    def next(self) -> None:
        if self._current_match is None or self._current_match.start == -1:
            return

        expr_length = len(
            tokenize_sql(self._expression_list[self._current_match.start : self._current_match.end])
        )
        start_token = self._current_match.start_token + expr_length - 1
        self._current_match = search(self._expression_list, self._list_element_pattern, start_token)
        if self._current_match.start != -1:
            self._split_expression()

    def get_expression_prefix(self) -> str:
        return self._expression_prefix

    def get_expression_suffix(self) -> str:
        return self._expression_suffix

    def get_full_expression(self) -> str:
        return self._expression_prefix + self._expression_suffix

    def get_list_prefix(self) -> str:
        return self._list_prefix

    def get_list_suffix(self) -> str:
        return self._list_suffix

    def is_single_column_reference(self) -> bool:
        tokens = tokenize_sql(self.get_expression_prefix())
        return (
            len(tokens) == 3
            and tokens[0].is_identifier()
            and tokens[1].text == "."
            and tokens[2].is_identifier()
        )

    def _split_list(self) -> None:
        self._list_prefix = ""
        self._list_suffix = ""

        if self._list_type == _ListType.SELECT:
            self._split_select()
        elif self._list_type == _ListType.GROUP_BY:
            self._split_group_by()

    def _split_select(self) -> None:
        match = search(
            "^" + self._expression_list + "$",
            parse_search_pattern("^ distinct @@a $"),
            0,
        )
        if match.start != -1:
            self._list_prefix = "distinct "
            self._expression_list = match.variable_to_value["@@a"]

        match = search(
            "^" + self._expression_list + "$",
            parse_search_pattern("^ @@a into @@b $"),
            0,
        )
        if match.start != -1:
            self._expression_list = match.variable_to_value["@@a"]
            self._list_suffix = " into " + match.variable_to_value["@@b"]

    def _split_group_by(self) -> None:
        match = search(
            "^" + self._expression_list + "$",
            parse_search_pattern("^ @@a order by @@b $"),
            0,
        )
        if match.start != -1:
            self._expression_list = match.variable_to_value["@@a"]
            self._list_suffix = " order by " + match.variable_to_value["@@b"]

    def _split_expression(self) -> None:
        assert self._current_match is not None
        self._expression_prefix = self._current_match.variable_to_value["@@a"]
        self._expression_suffix = ""

        if self._list_type == _ListType.SELECT:
            self._split_alias()
        elif self._list_type == _ListType.ORDER_BY:
            self._split_order_element()

    def _split_alias(self) -> None:
        tokens = tokenize_sql(self._expression_prefix)
        alias_pattern = parse_search_pattern("^ @@a as @@b $")
        alias_match = search("^" + self._expression_prefix + "$", alias_pattern, 0)
        if alias_match.start == -1:
            if len(tokens) >= 2:
                possible_alias = tokens[-1]
                preceding_token = tokens[-2].text
                if (
                    possible_alias.is_identifier()
                    and preceding_token.lower() != "."
                    and preceding_token.lower() != "+"
                ):
                    self._expression_prefix = self._expression_prefix[: possible_alias.start]
                    self._expression_suffix = possible_alias.text
        else:
            self._expression_prefix = alias_match.variable_to_value["@@a"]
            self._expression_suffix = alias_match.variable_to_value["@@b"]

    def _split_order_element(self) -> None:
        tokens = tokenize_sql(self.get_full_expression())
        last_token = tokens[-1]
        if last_token.text.lower() in ("asc", "desc"):
            self._expression_prefix = self.get_full_expression()[: last_token.start - 1]
            self._expression_suffix = " " + last_token.text


def _bigquery_alias_common_table_expressions(sql: str, pattern: str) -> str:
    cte_pattern = parse_search_pattern(pattern)
    cte_match = search(sql, cte_pattern, 0)
    while cte_match.start != -1:
        with_list_iter = _CommaListIterator(cte_match.variable_to_value["@@b"], _ListType.WITH_COLUMNS)
        select_list_iter = _CommaListIterator(cte_match.variable_to_value["@@c"], _ListType.SELECT)
        replacement_select_list = ""

        while not with_list_iter.is_done():
            if select_list_iter.is_done():
                break
            with_expr = with_list_iter.get_full_expression()
            select_expr = select_list_iter.get_expression_prefix() + " as " + with_expr
            if replacement_select_list:
                replacement_select_list = replacement_select_list + ","
            replacement_select_list = replacement_select_list + select_expr
            with_list_iter.next()
            select_list_iter.next()

        replacement_select_list = (
            select_list_iter.get_list_prefix() + replacement_select_list + select_list_iter.get_list_suffix()
        )

        d_val = cte_match.variable_to_value.get("@@d", "")
        if d_val is None:
            d_val = ""

        replacement = (
            pattern.replace("@@a", cte_match.variable_to_value["@@a"])
            .replace("(@@b)", "")
            .replace("@@c", replacement_select_list)
            .replace("@@d", d_val)
        )

        sql = sql[: cte_match.start] + replacement + sql[cte_match.end :]
        cte_match = search(sql, cte_pattern, cte_match.start_token + 1)

    return sql


def _bigquery_convert_select_list_references(sql: str, select_pattern: str, list_type: _ListType) -> str:
    select_statement_pattern = parse_search_pattern(select_pattern)
    select_statement_match = search(sql, select_statement_pattern, 0)

    while select_statement_match.start != -1:
        select_list = select_statement_match.variable_to_value["@@s"]
        list_to_replace = select_statement_match.variable_to_value["@@r"]
        replacement_list = ""

        list_to_replace_iter = _CommaListIterator(list_to_replace, list_type)
        while not list_to_replace_iter.is_done():
            list_expr = list_to_replace_iter.get_expression_prefix()
            list_expr_suffix = list_to_replace_iter.get_expression_suffix()
            list_expr_pattern = parse_search_pattern(list_expr)

            if list_to_replace_iter.is_single_column_reference():
                replacement_list = replacement_list + ", " + list_expr + list_expr_suffix
            else:
                select_list_iter = _CommaListIterator(select_list, _ListType.SELECT)
                found = False
                position = 1
                while not select_list_iter.is_done():
                    select_expr = select_list_iter.get_expression_prefix()
                    test_match = search(select_expr, list_expr_pattern, 0)
                    if test_match.start != -1:
                        found = True
                        replacement_list = replacement_list + ", " + str(position) + list_expr_suffix
                        break
                    select_list_iter.next()
                    position += 1
                if not found:
                    replacement_list = replacement_list + ", " + list_expr + list_expr_suffix

            list_to_replace_iter.next()

        if replacement_list.startswith(", "):
            replacement_list = replacement_list[2:]
        replacement_list = (
            list_to_replace_iter.get_list_prefix() + replacement_list + list_to_replace_iter.get_list_suffix()
        )

        suffix = sql[select_statement_match.end :]
        sql = sql[: select_statement_match.start]
        for i, block in enumerate(select_statement_pattern):
            if sql and i > 0:
                sql += " "
            if block.is_variable:
                if block.text == "@@r":
                    sql += replacement_list
                else:
                    sql += select_statement_match.variable_to_value.get(block.text, "")
            else:
                sql += block.text
        sql += suffix

        select_statement_match = search(sql, select_statement_pattern, select_statement_match.start_token + 1)

    return sql


def _bigquery_lower_case(sql: str) -> str:
    tokens = tokenize_sql(sql)
    result = list(sql)
    for token in tokens:
        if not token.in_quotes and not token.text.startswith("@"):
            lowered = token.text.lower()
            if lowered != token.text:
                result[token.start : token.end] = lowered
    return "".join(result)


def translate_bigquery(sql: str) -> str:
    sql = _bigquery_lower_case(sql)

    sql = _bigquery_alias_common_table_expressions(sql, "with @@a (@@b) as (select @@c from @@d)")
    sql = _bigquery_alias_common_table_expressions(sql, "with @@a (@@b) as (select @@c union @@d)")
    sql = _bigquery_alias_common_table_expressions(sql, "with @@a (@@b) as (select @@c)")
    sql = _bigquery_alias_common_table_expressions(sql, ", @@a (@@b) as (select @@c from @@d)")

    group_by_references = "select @@s from @@b group by @@r"
    sql = _bigquery_convert_select_list_references(sql, group_by_references + ";", _ListType.GROUP_BY)
    sql = _bigquery_convert_select_list_references(sql, group_by_references + ")", _ListType.GROUP_BY)
    sql = _bigquery_convert_select_list_references(sql, group_by_references + " having", _ListType.GROUP_BY)
    sql = _bigquery_convert_select_list_references(sql, group_by_references + " order by", _ListType.GROUP_BY)

    order_by = "select @@s from @@b order by @@r"
    sql = _bigquery_convert_select_list_references(sql, order_by + ";", _ListType.ORDER_BY)
    sql = _bigquery_convert_select_list_references(sql, order_by + ")", _ListType.ORDER_BY)

    return sql


def _spark_create_table(sql: str) -> str:
    if not sql.endswith(";"):
        sql += ";"

    pattern_str = "create table @@table (@@definition)"
    create_table_pattern = parse_search_pattern(pattern_str)
    sql_normalized = re.sub(r"\t", " ", sql.strip())
    sql_normalized = re.sub(r" +", " ", sql_normalized)

    create_table_match = search(sql_normalized, create_table_pattern, 0)
    if create_table_match.start == -1:
        return sql.replace(";", "")

    table_name = create_table_match.variable_to_value.get("@@table", "")
    definition_list = create_table_match.variable_to_value.get("@@definition", "")

    if not table_name or not definition_list:
        return sql.replace(";", "")

    table_name = re.sub(r"\r\n", "", table_name)
    definition_list = definition_list.lower().replace("\r\n", "").replace(" as ", " ")

    column_names: list[str] = []
    for f in definition_list.split(","):
        parts = f.strip().split(" ")
        if len(parts) >= 2:
            col_name = parts[0]
            col_type = parts[1]
            column_names.append(f"\tCAST(NULL AS {col_type}) AS {col_name}")

    prefix = sql[: create_table_match.start]
    sql = prefix + "SELECT " + ",\r\n".join(column_names) + " INTO " + table_name + " WHERE 1 = 0"

    return sql.replace(";", "")


def translate_spark(sql: str) -> str:
    from .splitter import split_sql

    splits = split_sql(sql)
    for i in range(len(splits)):
        splits[i] = _spark_create_table(splits[i])

    if len(splits) > 1 or sql.strip().endswith(";"):
        sql = ";\r\n".join(splits).strip() + ";"
    else:
        sql = ";\r\n".join(splits).strip()

    return sql
