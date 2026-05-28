import re
from dataclasses import dataclass, field

from .patterns import (
    MAX_TABLE_NAME_LENGTH,
    get_global_session_id,
    load_patterns,
)
from .tokenizer import tokenize_sql


class SqlTranslateError(RuntimeError):
    pass


@dataclass
class Block:
    start: int = 0
    end: int = 0
    text: str = ""
    in_quotes: bool = False
    is_variable: bool = False
    reg_ex: str | None = None


@dataclass
class MatchedPattern:
    start: int = -1
    end: int = -1
    start_token: int = -1
    variable_to_value: dict[str, str] = field(default_factory=dict)


def parse_search_pattern(pattern: str) -> list[Block]:
    tokens = tokenize_sql(pattern.lower())
    blocks: list[Block] = []
    i = 0
    while i < len(tokens):
        block = Block(
            start=tokens[i].start,
            end=tokens[i].end,
            text=tokens[i].text,
            in_quotes=tokens[i].in_quotes,
        )

        if len(block.text) > 2 and block.text[0] == "@":
            block.is_variable = True

        if block.text == "@@" and i < len(tokens) - 2 and tokens[i + 1].text == "(":
            escape = False
            nesting = 0
            for j in range(i + 2, len(tokens)):
                if escape:
                    escape = False
                elif tokens[j].text == "\\":
                    escape = True
                elif not escape and tokens[j].text == "(":
                    nesting += 1
                elif not escape and tokens[j].text == ")":
                    if nesting == 0:
                        block.text = "@@" + tokens[j + 1].text
                        block.reg_ex = pattern[tokens[i + 1].end : tokens[j].start]
                        block.end = tokens[j + 1].end
                        block.is_variable = True
                        i = j + 1
                        break
                    nesting -= 1
            blocks.append(block)
            i += 1
            continue

        blocks.append(block)
        i += 1

    if blocks and blocks[0].is_variable and blocks[0].reg_ex is None:
        raise SqlTranslateError(
            "Error in search pattern: pattern cannot start or end with a non-regex variable: " + pattern
        )
    if blocks and blocks[-1].is_variable and blocks[-1].reg_ex is None:
        raise SqlTranslateError(
            "Error in search pattern: pattern cannot start or end with a non-regex variable: " + pattern
        )

    return blocks


def _matches(regex: str, string: str) -> bool:
    return bool(re.match(regex, string, re.DOTALL | re.MULTILINE | re.IGNORECASE))


def _matches_end(regex: str, string: str) -> int:
    stripped = re.sub(r"\s+$", "", string)
    pattern = re.compile(regex, re.DOTALL | re.MULTILINE | re.IGNORECASE)
    start = -1
    for m in pattern.finditer(stripped):
        if m.end() == len(stripped):
            start = m.start()
    return start


def search(sql: str, parsed_pattern: list[Block], start_token: int = 0) -> MatchedPattern:
    lowercase_sql = sql.lower()
    tokens = tokenize_sql(lowercase_sql)
    match_count = 0
    var_start = 0
    nest_stack: list[str] = []
    in_pattern_quote = False
    matched = MatchedPattern()

    cursor = start_token
    while cursor < len(tokens):
        token = tokens[cursor]

        if parsed_pattern[match_count].is_variable:
            block = parsed_pattern[match_count]

            if block.reg_ex is not None and (
                match_count == len(parsed_pattern) - 1 or parsed_pattern[match_count + 1].is_variable
            ):
                pat = re.compile(block.reg_ex, re.DOTALL | re.MULTILINE | re.IGNORECASE)
                m = pat.match(sql[token.start :])
                if m and m.start() == 0:
                    if match_count == 0:
                        matched.start = token.start
                        matched.start_token = cursor
                    matched.variable_to_value[block.text] = sql[token.start : token.start + m.end()]
                    match_count += 1
                    if match_count == len(parsed_pattern):
                        matched.end = token.start + m.end()
                        return matched
                    elif parsed_pattern[match_count].is_variable:
                        var_start = token.start + m.end()
                    while cursor < len(tokens) and tokens[cursor].start < token.start + m.end():
                        cursor += 1
                    cursor -= 1
                else:
                    match_count = 0
                cursor += 1
                continue

            if (
                len(nest_stack) == 0
                and match_count < len(parsed_pattern) - 1
                and token.text == parsed_pattern[match_count + 1].text
            ):
                if block.reg_ex is not None and match_count == 0:
                    s = _matches_end(block.reg_ex, sql[var_start : token.start])
                    if s != -1:
                        matched.variable_to_value[block.text] = sql[var_start + s : token.start]
                        matched.start = var_start + s
                        matched.start_token = cursor
                        match_count += 2
                        if match_count == len(parsed_pattern):
                            matched.end = token.end
                            return matched
                        elif parsed_pattern[match_count].is_variable:
                            var_start = tokens[cursor + 1].start if cursor < len(tokens) - 1 else -1
                        if token.text in ("'", '"'):
                            in_pattern_quote = not in_pattern_quote
                    else:
                        match_count = 0
                        cursor = matched.start_token
                elif block.reg_ex is not None and not _matches(block.reg_ex, sql[var_start : token.start]):
                    match_count = 0
                    cursor = matched.start_token
                else:
                    matched.variable_to_value[block.text] = sql[var_start : token.start]
                    match_count += 2
                    if match_count == len(parsed_pattern):
                        matched.end = token.end
                        return matched
                    elif parsed_pattern[match_count].is_variable:
                        var_start = tokens[cursor + 1].start if cursor < len(tokens) - 1 else -1
                    if token.text in ("'", '"'):
                        in_pattern_quote = not in_pattern_quote
                cursor += 1
                continue

            if (
                match_count != 0
                and len(nest_stack) == 0
                and not in_pattern_quote
                and token.text in (";", ")")
            ):
                match_count = 0
                cursor = matched.start_token
                cursor += 1
                continue

            if nest_stack:
                top = nest_stack[-1]
                if top in ('"', "'"):
                    if token.text == top:
                        nest_stack.pop()
                else:
                    if token.text in ('"', "'") or not in_pattern_quote and token.text == "(":
                        nest_stack.append(token.text)
                    elif not in_pattern_quote and nest_stack and token.text == ")" and nest_stack[-1] == "(":
                        nest_stack.pop()
            else:
                if token.text in ('"', "'") or not in_pattern_quote and token.text == "(":
                    nest_stack.append(token.text)
                elif not in_pattern_quote and nest_stack and token.text == ")" and nest_stack[-1] == "(":
                    nest_stack.pop()
            cursor += 1
            continue

        if token.text == parsed_pattern[match_count].text and (match_count != 0 or not token.in_quotes):
            if match_count == 0:
                matched.start = token.start
                matched.start_token = cursor
            match_count += 1
            if match_count == len(parsed_pattern):
                matched.end = token.end
                return matched
            elif parsed_pattern[match_count].is_variable:
                var_start = tokens[cursor + 1].start if cursor < len(tokens) - 1 else -1
            if token.text in ("'", '"'):
                in_pattern_quote = not in_pattern_quote
        elif match_count != 0:
            match_count = 0
            cursor = matched.start_token

        cursor += 1

        if match_count != 0 and cursor >= len(tokens):
            match_count = 0
            cursor = matched.start_token + 1

    matched.start = -1
    return matched


def search_and_replace(sql: str, parsed_pattern: list[Block], replace_pattern: str) -> str:
    matched = search(sql, parsed_pattern, 0)
    while matched.start != -1:
        replacement = replace_pattern
        for var_name, var_value in matched.variable_to_value.items():
            replacement = replacement.replace(var_name, var_value)
        sql = sql[: matched.start] + replacement + sql[matched.end :]

        delta = 1
        repl_tokens = tokenize_sql(replacement)
        if len(repl_tokens) == 0:
            delta = 0
        if (
            delta > 0
            and replace_pattern.startswith("@@")
            and replacement.lower().strip().startswith(parsed_pattern[0].text)
        ):
            delta = 0
        matched = search(sql, parsed_pattern, matched.start_token + delta)
    return sql


def _strip_blank_lines(sql: str) -> str:
    return re.sub(r"(?m)^[ \t]*\r?\n", "", sql)


def translate(
    sql: str,
    target_dialect: str,
    session_id: str | None = None,
    temp_emulation_schema: str | None = None,
) -> str:
    patterns = load_patterns()

    if session_id is None:
        session_id = get_global_session_id()
    else:
        if len(session_id) != 8:
            raise SqlTranslateError(f"Session ID has length {len(session_id)}, should be 8")
        if not session_id[0].isalpha():
            raise SqlTranslateError("Session ID does not start with a letter")
        for ch in session_id[1:]:
            if not ch.isalnum():
                raise SqlTranslateError(f"Illegal character in session ID: {ch}")

    oracle_temp_prefix = ""
    if temp_emulation_schema is not None:
        oracle_temp_prefix = temp_emulation_schema + "."

    replacement_patterns = patterns.get(target_dialect)
    if replacement_patterns is None:
        supported = ", ".join(sorted(patterns.keys()))
        raise SqlTranslateError(
            f"Don't know how to translate to {target_dialect}. Valid target dialects are {supported}"
        )

    for pattern, replacement in replacement_patterns:
        replacement = replacement.replace("%session_id%", session_id)
        replacement = replacement.replace("%temp_prefix%", oracle_temp_prefix)
        parsed = parse_search_pattern(pattern)
        sql = _strip_blank_lines(search_and_replace(sql, parsed, replacement))

    sql = _strip_blank_lines(sql)

    lower = target_dialect.lower()
    if lower in ("impala", "bigquery", "spark"):
        sql = _replace_with_concat(sql)

    return sql


def _replace_with_concat(val: str) -> str:
    pattern = re.compile(r"(?<!\\)'(''|[^'])*'")
    result = []
    last_end = 0
    for m in pattern.finditer(val):
        result.append(val[last_end : m.start()])
        s = m.group()
        if "''" in s and s != "''":
            result.append(_escape_quotes_for_concat(s))
        else:
            result.append(s)
        last_end = m.end()
    result.append(val[last_end:])
    return "".join(result)


def _escape_quotes_for_concat(s: str) -> str:
    inner = s[1:-1]
    parts = inner.split("''")
    concat_parts = []
    for part in parts:
        if part == "":
            concat_parts.append("'\\047'")
        else:
            escaped = part.replace("\\", "\\\\").replace('"', "\\042").replace("/", "\\/")
            concat_parts.append("'" + escaped + "'")
    return "CONCAT(" + ",".join(concat_parts) + ")"


def check(sql: str, target_dialect: str) -> list[str]:
    warnings: list[str] = []
    pattern = re.compile(r"#[0-9a-zA-Z_]+")
    long_temp_names: set[str] = set()
    for m in pattern.finditer(sql):
        name = m.group()
        if len(name) > MAX_TABLE_NAME_LENGTH - 8 - 1:
            long_temp_names.add(name)
    for name in sorted(long_temp_names):
        warnings.append(
            f"Temp table name '{name}' is too long. Temp table names should be shorter than "
            f"{MAX_TABLE_NAME_LENGTH - 8} characters to prevent some DMBSs from throwing an error."
        )

    pattern2 = re.compile(r"(create|drop|truncate)\s+table\s+[0-9a-zA-Z_]+", re.IGNORECASE)
    long_names: set[str] = set()
    for m in pattern2.finditer(sql):
        name = m.group().split()[-1]
        if len(name) > MAX_TABLE_NAME_LENGTH and "#" + name not in long_temp_names:
            long_names.add(name)
    for name in sorted(long_names):
        warnings.append(
            f"Table name '{name}' is too long. Table names should be shorter than "
            f"{MAX_TABLE_NAME_LENGTH} characters to prevent some DMBSs from throwing an error."
        )
    return warnings


def generate_session_id() -> str:
    from .patterns import generate_session_id as _gen

    return _gen()


def set_replacement_patterns_path(path: str | None) -> None:
    from .patterns import set_replacement_patterns_path as _set

    _set(path)
