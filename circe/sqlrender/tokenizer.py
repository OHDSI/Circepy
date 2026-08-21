from __future__ import annotations

from dataclasses import dataclass

HINT_KEY_WORD = "hint"


@dataclass
class Token:
    start: int = 0
    end: int = 0
    text: str = ""
    in_quotes: bool = False

    def is_identifier(self) -> bool:
        return all(ch.isalnum() or ch == "_" for ch in self.text)


def tokenize_sql(sql: str) -> list[Token]:
    """Splits the SQL into tokens.

    Any alphanumeric (including underscore and @) sequence is considered a token.
    All other individual special characters are considered their own tokens.
    White space and SQL comments are not considered for tokens.
    """
    tokens: list[Token] = []
    start = 0
    cursor = 0
    comment_type1 = False  # -- ... end of line
    comment_type2 = False  # /* .. */
    in_single_quotes = False
    in_double_quotes = False

    while cursor < len(sql):
        ch = sql[cursor]

        if comment_type1:
            if ch == "\n":
                comment_type1 = False
                start = cursor + 1
            cursor += 1
            continue

        if comment_type2:
            if ch == "/" and cursor > 0 and sql[cursor - 1] == "*":
                comment_type2 = False
                start = cursor + 1
            cursor += 1
            continue

        if not (ch.isalnum() or ch == "_" or ch == "@"):
            if cursor > start:
                token = Token(
                    start=start,
                    end=cursor,
                    text=sql[start:cursor],
                    in_quotes=in_single_quotes or in_double_quotes,
                )
                tokens.append(token)

            if (
                ch == "-"
                and cursor + 1 < len(sql)
                and sql[cursor + 1] == "-"
                and not in_single_quotes
                and not in_double_quotes
                and (len(sql) - cursor < 6 or sql[cursor + 2 : cursor + 6].lower() != HINT_KEY_WORD)
            ):
                comment_type1 = True
            elif (
                ch == "/"
                and cursor + 1 < len(sql)
                and sql[cursor + 1] == "*"
                and not in_single_quotes
                and not in_double_quotes
            ):
                comment_type2 = True
            elif not ch.isspace():
                token = Token(
                    start=cursor,
                    end=cursor + 1,
                    text=sql[cursor],
                    in_quotes=in_single_quotes or in_double_quotes,
                )
                tokens.append(token)
                if ch == "'" and not in_double_quotes:
                    in_single_quotes = not in_single_quotes
                if ch == '"' and not in_single_quotes:
                    in_double_quotes = not in_double_quotes

            start = cursor + 1
            cursor += 1
        else:
            cursor += 1

    if cursor > start and not comment_type1 and not comment_type2:
        token = Token(
            start=start,
            end=cursor,
            text=sql[start:cursor],
            in_quotes=in_single_quotes or in_double_quotes,
        )
        tokens.append(token)

    return tokens
