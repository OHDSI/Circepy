import re
from typing import Any


class SqlRenderError(RuntimeError):
    pass


def _evaluate_condition(condition: str, params: dict[str, Any]) -> bool:
    condition = condition.strip()

    if condition.lower() == "true":
        return True
    if condition.lower() == "false":
        return False

    if condition.startswith("!"):
        return not _evaluate_condition(condition[1:].strip(), params)

    m = re.match(r"\((.+)\)", condition)
    if m:
        return _evaluate_condition(m.group(1).strip(), params)

    m = re.match(r"(.+?)\s+(!=|<>)+\s+(.+)", condition)
    if m:
        left = m.group(1).strip()
        right = m.group(3).strip()
        lval = _resolve_value(left, params)
        rval = _resolve_value(right, params)
        return str(lval) != str(rval)

    m = re.match(r"(.+?)\s*==\s*(.+)", condition)
    if m:
        left = m.group(1).strip()
        right = m.group(2).strip()
        lval = _resolve_value(left, params)
        rval = _resolve_value(right, params)
        return str(lval) == str(rval)

    m = re.match(r"([\d.]+|\w+)\s+IN\s+\((.+)\)", condition, re.IGNORECASE | re.DOTALL)
    if m:
        val = _resolve_value(m.group(1).strip(), params)
        in_list_raw = m.group(2).strip()
        in_list = []
        for item in re.split(r",\s*", in_list_raw):
            item = item.strip()
            is_param_ref = item.startswith("@") and item[1:] in params
            resolved = _resolve_value(item, params) if is_param_ref else item
            if isinstance(resolved, list):
                in_list.extend(str(x) for x in resolved)
            else:
                in_list.append(str(resolved))
        return str(val) in in_list

    m = re.match(r"(.+?)\s*&\s*(.+)", condition)
    if m:
        return _evaluate_condition(m.group(1).strip(), params) and _evaluate_condition(
            m.group(2).strip(), params
        )

    m = re.match(r"(.+?)\s*\|\s*(.+)", condition)
    if m:
        return _evaluate_condition(m.group(1).strip(), params) or _evaluate_condition(
            m.group(2).strip(), params
        )

    if condition.startswith("@"):
        param_name = condition[1:]
        val = params.get(param_name)
        return val is not None and (
            (isinstance(val, bool) and val) or (isinstance(val, str) and val.lower() == "true")
        )

    raise SqlRenderError(f"Invalid boolean logic: {condition}")


def _resolve_value(expr: str, params: dict[str, Any]) -> Any:
    expr = expr.strip()
    if expr.startswith("@") and len(expr) > 1:
        param_name = expr[1:]
        return params.get(param_name, expr)
    if expr.startswith("'") and expr.endswith("'"):
        return expr[1:-1]
    return expr


def render(sql: str, **params: Any) -> str:
    has_unused_params = any(re.search(r"@" + re.escape(k) + r"\b", sql) is None for k in params)
    if has_unused_params:
        import warnings as _warnings

        _warnings.warn("Parameter name mismatch in render call", stacklevel=2)

    sql = _apply_defaults(sql, params)
    sql = _process_conditionals(sql, params)
    sql = _substitute_params(sql, params)
    return sql


DEFAULT_PATTERN = re.compile(r"\{DEFAULT\s+@(\w+)\s*=\s*([^}]+)\}")


def _apply_defaults(sql: str, params: dict[str, Any]) -> dict[str, Any]:
    def extract_default(m: re.Match) -> str:
        name = m.group(1)
        value = m.group(2).strip()
        if name not in params:
            if value.startswith("'") and value.endswith("'"):
                params[name] = value[1:-1]
            else:
                params[name] = value
        return ""

    sql = DEFAULT_PATTERN.sub(extract_default, sql)
    return sql


def _find_matching_brace(s: str, start: int) -> int:
    depth = 0
    in_single = False
    in_double = False
    i = start
    while i < len(s):
        ch = s[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if in_single or in_double:
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _extract_braced_block(s: str, start: int) -> tuple[str, int]:
    end = _find_matching_brace(s, start)
    if end == -1:
        return "", start
    return s[start + 1 : end], end


def _process_conditionals(sql: str, params: dict[str, Any]) -> str:
    result = sql

    for _pass in range(100):
        i = 0
        modified = False
        while i < len(result):
            ch = result[i]
            if ch == "{":
                close = _find_matching_brace(result, i)
                if close == -1:
                    i += 1
                    continue

                inner = result[i + 1 : close]
                rest_after_close = close + 1

                if inner.startswith("DEFAULT "):
                    pass

                elif rest_after_close < len(result) and result[rest_after_close] == "?":
                    condition_text = inner
                    after_q = rest_after_close + 1

                    if after_q < len(result) and result[after_q] == "{":
                        then_block, then_end = _extract_braced_block(result, after_q)
                        then_text = then_block
                        after_then = then_end + 1

                        else_text = ""
                        if after_then < len(result) and result[after_then] == ":":
                            after_colon = after_then + 1
                            if after_colon < len(result) and result[after_colon] == "{":
                                else_block, else_end = _extract_braced_block(result, after_colon)
                                else_text = else_block
                                after_else = else_end + 1
                            else:
                                after_else = after_colon
                        else:
                            after_else = after_then

                        cond_result = _evaluate_condition(condition_text, params)

                        replacement = then_text if cond_result else else_text
                        result = result[:i] + replacement + result[after_else:]
                        modified = True
                        break

                else:
                    pass

            i += 1

        if not modified:
            break

    return result


def _substitute_params(sql: str, params: dict[str, Any]) -> str:
    def repl(m: re.Match) -> str:
        name = m.group(1)
        if name in params:
            val = params[name]
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            if isinstance(val, bool):
                return str(val).lower()
            return str(val)
        return m.group(0)

    return re.sub(r"@(\w+)", repl, sql)
