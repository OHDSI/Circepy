from __future__ import annotations

import re
from dataclasses import dataclass, field

from .patterns import MAX_TABLE_NAME_LENGTH, get_global_session_id, load_patterns
from .tokenizer import tokenize_sql


class SqlTranslateError(RuntimeError):
    pass


@dataclass
class _Block:
    start: int = 0
    end: int = 0
    text: str = ""
    in_quotes: bool = False
    is_variable: bool = False
    reg_ex: str | None = None


@dataclass
class _MatchedPattern:
    start: int = -1
    end: int = -1
    start_token: int = -1
    variable_to_value: dict[str, str] = field(default_factory=dict)


def parse_search_pattern(pattern: str) -> list[_Block]:
    tokens = tokenize_sql(pattern.lower())
    blocks: list[_Block] = []

    i = 0
    while i < len(tokens):
        block = _Block(
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
    pattern = re.compile(regex, re.DOTALL | re.MULTILINE | re.IGNORECASE)
    return bool(pattern.fullmatch(string))


def _matches_end(regex: str, string: str) -> int:
    string = re.sub(r"\s+$", "", string)
    pattern = re.compile(regex, re.DOTALL | re.MULTILINE | re.IGNORECASE)
    start = -1
    for m in pattern.finditer(string):
        if m.end() == len(string):
            start = m.start()
    return start


def search(sql: str, parsed_pattern: list[_Block], start_token: int = 0) -> _MatchedPattern:
    lowercase_sql = sql.lower()
    tokens = tokenize_sql(lowercase_sql)

    match_count = 0
    var_start = 0
    nest_stack: list[str] = []
    in_pattern_quote = False
    matched = _MatchedPattern()

    cursor = start_token
    while cursor < len(tokens):
        token = tokens[cursor]

        if parsed_pattern[match_count].is_variable:
            block = parsed_pattern[match_count]

            # Regex variable at end of pattern or followed by another variable
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

            # Check for token match after the variable
            if (
                len(nest_stack) == 0
                and match_count < len(parsed_pattern) - 1
                and token.text == parsed_pattern[match_count + 1].text
            ):
                if block.reg_ex is not None and match_count == 0:
                    # First element is regex. Find last part of string prior to
                    # subsequent token that matches the regex:
                    m_end = _matches_end(block.reg_ex, sql[var_start : token.start])
                    if m_end != -1:
                        matched.variable_to_value[block.text] = sql[var_start + m_end : token.start]
                        matched.start = var_start + m_end
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
                    # Content didn't match regex
                    match_count = 0
                    cursor = matched.start_token
                else:
                    # No regex or matched regex
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

            # Not allowed to span multiple SQL statements or outside of nesting
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

            # Track nesting
            if nest_stack:
                top = nest_stack[-1]
                if top in ('"', "'"):
                    if token.text == top:
                        nest_stack.pop()
                else:
                    if token.text in ('"', "'") or (not in_pattern_quote and token.text == "("):
                        nest_stack.append(token.text)
                    elif not in_pattern_quote and nest_stack and token.text == ")" and nest_stack[-1] == "(":
                        nest_stack.pop()
            else:
                if token.text in ('"', "'") or (not in_pattern_quote and token.text == "("):
                    nest_stack.append(token.text)
                elif not in_pattern_quote and nest_stack and token.text == ")" and nest_stack[-1] == "(":
                    nest_stack.pop()
            cursor += 1
            continue

        # Non-variable: check if token matches current part of pattern
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

        # If at end of sql and still didn't finish pattern, we're not going to finish it
        if match_count != 0 and cursor >= len(tokens):
            match_count = 0
            cursor = matched.start_token + 1

    matched.start = -1
    return matched


def search_and_replace(sql: str, parsed_pattern: list[_Block], replace_pattern: str) -> str:
    matched = search(sql, parsed_pattern, 0)
    while matched.start != -1:
        replacement = replace_pattern
        for var_name, var_value in matched.variable_to_value.items():
            pos = 0
            while True:
                pos = replacement.find(var_name, pos)
                if pos == -1:
                    break
                replacement = replacement[:pos] + var_value + replacement[pos + len(var_name) :]
                pos += len(var_value)

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


def _replace_all(s: str, search_str: str, replace_str: str) -> str:
    pos = 0
    while True:
        pos = s.find(search_str, pos)
        if pos == -1:
            break
        s = s[:pos] + replace_str + s[pos + len(search_str) :]
        pos += len(replace_str)
    return s


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

    lower = target_dialect.lower()
    if lower == "bigquery":
        from .bigquery_spark import translate_bigquery

        sql = translate_bigquery(sql)
    elif lower == "spark":
        from .bigquery_spark import translate_spark

        sql = translate_spark(sql)

    for pattern, replacement in replacement_patterns:
        replacement = replacement.replace("%session_id%", session_id)
        replacement = replacement.replace("%temp_prefix%", oracle_temp_prefix)
        parsed = parse_search_pattern(pattern)
        sql = _strip_blank_lines(search_and_replace(sql, parsed, replacement))

    sql = _strip_blank_lines(sql)

    if lower in ("impala", "bigquery", "spark"):
        sql = _replace_with_concat(sql)

    return sql


def _replace_with_concat(val: str) -> str:
    tokens = _split_and_keep(val, r"""(['\"])((?!\1).|\1{2})*\1""")
    result: list[str] = []
    for token in tokens:
        if re.match(r"""(['\"])((?!\1).|\1{2})*\1""", token) and "''" in token:
            result.append(_escape_quotes_for_concat(token))
        else:
            result.append(token)
    return "".join(result)


def _split_and_keep(val: str, regex: str) -> list[str]:
    result: list[str] = []
    pos = 0
    for m in re.finditer(regex, val):
        if m.start() > pos:
            result.append(val[pos : m.start()])
        result.append(m.group())
        pos = m.end()
    if pos < len(val):
        result.append(val[pos:])
    return result


def _escape_quotes_for_concat(s: str) -> str:
    if s == "''":
        return s

    inner = s[1:-1]
    parts = _split_and_keep(inner, "''")
    concat_parts: list[str] = []
    for _i, part in enumerate(parts):
        if part == "''":
            concat_parts.append("'\\047'")
        else:
            escaped = part.replace("'", "")
            escaped = escaped.replace("\\", "\\\\")
            escaped = escaped.replace('"', "\\042")
            escaped = escaped.replace("/", "\\/")
            concat_parts.append("'" + escaped + "'")
    return "CONCAT(" + ",".join(concat_parts) + ")"


def check(sql: str, target_dialect: str) -> list[str]:
    warnings: list[str] = []

    # temp table names
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

    # normal table names
    pattern2 = re.compile(r"(create|drop|truncate)\s+table +[0-9a-zA-Z_]+", re.IGNORECASE)
    long_names: set[str] = set()
    for m in pattern2.finditer(sql.lower()):
        full_match = sql[m.start() : m.end()]
        name = full_match[full_match.rindex(" ") + 1 :]
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
