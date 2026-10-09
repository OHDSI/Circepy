from __future__ import annotations

from .tokenizer import tokenize_sql


def split_sql(sql: str) -> list[str]:
    """Splits a string containing multiple SQL statements into a list of SQL statements."""
    parts: list[str] = []
    tokens = tokenize_sql(sql.lower())
    nest_stack: list[str] = []
    last_pop = ""
    start = 0
    cursor = 0
    quote = False
    bracket = False
    quote_text = ""

    while cursor < len(tokens):
        token = tokens[cursor]

        if quote:
            if token.text == quote_text:
                quote = False
        elif bracket:
            if token.text == "]":
                bracket = False
        elif token.text in ("'", '"'):
            quote = True
            quote_text = token.text
        elif token.text == "[":
            bracket = True
        elif token.text in ("begin", "case"):
            nest_stack.append(token.text)
        elif token.text == "end" and (cursor == len(tokens) - 1 or tokens[cursor + 1].text != "if"):
            if nest_stack:
                last_pop = nest_stack.pop()
        elif len(nest_stack) == 0 and token.text == ";":
            if cursor == 0 or (tokens[cursor - 1].text == "end" and last_pop == "begin"):
                parts.append(sql[tokens[start].start : token.end])
            else:
                parts.append(sql[tokens[start].start : token.end - 1])
            start = cursor + 1
        cursor += 1

    if start < cursor:
        parts.append(sql[tokens[start].start : tokens[cursor - 1].end])

    return parts
