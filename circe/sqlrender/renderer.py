from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class SqlRenderError(RuntimeError):
    pass


@dataclass
class _Span:
    start: int
    end: int
    valid: bool = True


@dataclass
class _IfThenElse:
    condition: _Span
    if_true: _Span
    if_false: _Span | None = None
    has_if_false: bool = False

    def spans_end(self) -> int:
        if self.has_if_false and self.if_false is not None:
            return self.if_false.end
        return self.if_true.end


def _find_curly_bracket_spans(s: str) -> list[_Span]:
    starts: list[int] = []
    spans: list[_Span] = []
    for i, ch in enumerate(s):
        if ch == "{":
            starts.append(i)
        elif ch == "}" and starts:
            spans.append(_Span(start=starts.pop(), end=i + 1))
    return spans


def _find_parentheses(s: str) -> list[_Span]:
    starts: list[int] = []
    spans: list[_Span] = []
    for i, ch in enumerate(s):
        if ch == "(":
            starts.append(i)
        elif ch == ")" and starts:
            spans.append(_Span(start=starts.pop(), end=i + 1))
    return spans


def _link_if_then_elses(s: str, spans: list[_Span]) -> list[_IfThenElse]:
    result: list[_IfThenElse] = []
    if len(spans) <= 1:
        return result

    for i in range(len(spans) - 1):
        for j in range(i + 1, len(spans)):
            if spans[j].start > spans[i].end:
                in_between = s[spans[i].end : spans[j].start].strip()
                if in_between == "?":
                    ite = _IfThenElse(condition=spans[i], if_true=spans[j])
                    if j < len(spans):
                        for k in range(j + 1, len(spans)):
                            if spans[k].start > spans[j].end:
                                in_between2 = s[spans[j].end : spans[k].start].strip()
                                if in_between2 == ":":
                                    ite.if_false = spans[k]
                                    ite.has_if_false = True
                    result.append(ite)
    return result


def _preceded_by_in(start: int, s: str) -> bool:
    s = s.lower()
    matched = 0
    for i in range(start - 1, -1, -1):
        ch = s[i]
        if not ch.isspace():
            if matched == 0 and ch == "n" or matched == 1 and ch == "i":
                matched += 1
            else:
                return False
        elif matched == 2:
            return True
    return False


def _remove_parentheses(s: str) -> str:
    if len(s) > 1 and ((s[0] == "'" and s[-1] == "'") or (s[0] == '"' and s[-1] == '"')):
        return s[1:-1]
    return s


def _evaluate_primitive_condition(s: str) -> bool:
    s = s.strip()
    s_lc = s.lower()
    if s_lc in ("false", "0", "!true", "!1"):
        return False
    if s_lc in ("true", "1", "!false", "!0"):
        return True

    found = s.find("==")
    if found != -1:
        left = s[:found].strip()
        left = _remove_parentheses(left)
        right = s[found + 2 :].strip()
        right = _remove_parentheses(right)
        return left == right

    found = s.find("!=")
    if found == -1:
        found = s.find("<>")
    if found != -1:
        left = s[:found].strip()
        left = _remove_parentheses(left)
        right = s[found + 2 :].strip()
        right = _remove_parentheses(right)
        return left != right

    found = s_lc.find(" in ")
    if found != -1:
        left = s[:found].strip()
        left = _remove_parentheses(left)
        right = s[found + 4 :].strip()
        if len(right) > 2 and right[0] == "(" and right[-1] == ")":
            right = right[1:-1]
            parts = right.split(",")
            return any(left == _remove_parentheses(part.strip()) for part in parts)

    raise SqlRenderError(f'Error parsing boolean condition: "{s}"')


def _evaluate_boolean_condition(s: str) -> bool:
    s = s.strip()

    found = s.find("&")
    if found != -1:
        parts = s.split("&")
        return all(_evaluate_primitive_condition(part) for part in parts)

    found = s.find("|")
    if found != -1:
        parts = s.split("|")
        return any(_evaluate_primitive_condition(part) for part in parts)

    return _evaluate_primitive_condition(s)


def _evaluate_condition(s: str) -> bool:
    s = s.strip()
    spans = _find_parentheses(s)
    for span in spans:
        if not _preceded_by_in(span.start, s):
            evaluation = _evaluate_boolean_condition(s[span.start + 1 : span.end - 1])
            # Replace opening paren with '1'/'0'
            s = s[: span.start] + ("1" if evaluation else "0") + s[span.start + 1 :]
            # Collapse the entire (...) to just the single digit, adjusting other spans
            s = _replace_spans(s, spans, span.start, span.end, span.start, span.start)
    return _evaluate_boolean_condition(s)


def _replace_spans(
    s: str,
    spans: list[_Span],
    to_replace_start: int,
    to_replace_end: int,
    replace_with_start: int,
    replace_with_end: int,
) -> str:
    replace_with_str = ""
    if replace_with_end >= 0:
        replace_with_str = s[replace_with_start : replace_with_end + 1]

    s = s[:to_replace_start] + replace_with_str + s[to_replace_end:]

    for span in spans:
        if not span.valid:
            continue
        if span.start > to_replace_start:
            if span.start >= replace_with_start and span.start < replace_with_end:
                delta = to_replace_start - replace_with_start
                span.start += delta
                span.end += delta
            elif span.start > to_replace_end:
                delta = to_replace_start - to_replace_end + len(replace_with_str)
                span.start += delta
                span.end += delta
            else:
                span.valid = False
        elif span.end > to_replace_end:
            delta = to_replace_start - to_replace_end + len(replace_with_str)
            span.end += delta

    return s


def _extract_defaults(s: str) -> dict[str, str]:
    defaults: dict[str, str] = {}
    default_start = 0
    default_end = 0
    pre = "{DEFAULT "
    post = "}"
    while default_start != -1 and default_end != -1:
        default_start = s.find(pre, default_end)
        if default_start != -1:
            default_end = s.find(post, default_start + len(pre))
            if default_end != -1:
                span = s[default_start + len(pre) : default_end]
                found = span.find("=")
                if found != -1:
                    parameter = span[:found].strip()
                    if len(parameter) > 0 and parameter[0] == "@":
                        parameter = parameter[1:]
                    default_value = span[found + 2 :].strip()
                    default_value = _remove_parentheses(default_value)
                    defaults[parameter] = default_value
    return defaults


def _remove_defaults(s: str) -> str:
    return re.sub(r"\{DEFAULT[^}]*\}\s*\n?", "", s)


def _escape_dollar_sign(s: str) -> str:
    if "$" not in s:
        return s
    result: list[str] = []
    for ch in s:
        if ch == "$":
            result.append("\\")
        result.append(ch)
    return "".join(result)


def _substitute_parameters(s: str, parameter_to_value: dict[str, str]) -> str:
    defaults = _extract_defaults(s)
    s = _remove_defaults(s)
    for key, val in defaults.items():
        if key not in parameter_to_value:
            parameter_to_value[key] = val

    # Sort parameters longest to shortest so substring matches don't interfere
    sorted_params = sorted(parameter_to_value.items(), key=lambda x: len(x[0]), reverse=True)
    for key, value in sorted_params:
        value = value.replace("\\", "\\\\")
        s = re.sub(r"@" + re.escape(key), _escape_dollar_sign(value), s)

    return s


def _parse_if_then_else(s: str) -> str:
    spans = _find_curly_bracket_spans(s)
    if_then_elses = _link_if_then_elses(s, spans)

    result = s
    for ite in if_then_elses:
        if ite.condition.valid:
            cond_text = result[ite.condition.start + 1 : ite.condition.end - 1]
            if _evaluate_condition(cond_text):
                result = _replace_spans(
                    result,
                    spans,
                    ite.condition.start,
                    ite.spans_end(),
                    ite.if_true.start + 1,
                    ite.if_true.end - 2,
                )
            else:
                if ite.has_if_false and ite.if_false is not None:
                    result = _replace_spans(
                        result,
                        spans,
                        ite.condition.start,
                        ite.spans_end(),
                        ite.if_false.start + 1,
                        ite.if_false.end - 2,
                    )
                else:
                    result = _replace_spans(
                        result,
                        spans,
                        ite.condition.start,
                        ite.spans_end(),
                        0,
                        -1,
                    )
    return result


def render(sql: str, **params: Any) -> str:
    parameter_to_value: dict[str, str] = {}
    for key, val in params.items():
        if isinstance(val, bool):
            parameter_to_value[key] = str(val).lower()
        elif isinstance(val, list):
            parameter_to_value[key] = ", ".join(str(v) for v in val)
        else:
            parameter_to_value[key] = str(val)

    result = _substitute_parameters(sql, parameter_to_value)
    result = _parse_if_then_else(result)
    return result


def check(sql: str, parameters: list[str] | None = None, values: list[str] | None = None) -> list[str]:
    warnings_list: list[str] = []
    if parameters is not None:
        for param in parameters:
            if "@" + param not in sql:
                warnings_list.append(f"Parameter '{param}' not found in SQL")
    return warnings_list
