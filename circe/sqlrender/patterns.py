import random
import string

_target_to_patterns: dict[str, list[tuple[str, str]]] | None = None
_global_session_id: str | None = None
_PATTERNS_PATH: str | None = None

SESSION_ID_LENGTH = 8
MAX_TABLE_NAME_LENGTH = 63


def generate_session_id() -> str:
    chars = string.ascii_lowercase + "0123456789"
    first = random.choice(string.ascii_lowercase)
    rest = "".join(random.choice(chars) for _ in range(SESSION_ID_LENGTH - 1))
    return first + rest


def get_global_session_id() -> str:
    global _global_session_id
    if _global_session_id is None:
        _global_session_id = generate_session_id()
    return _global_session_id


def set_replacement_patterns_path(path: str | None) -> None:
    global _target_to_patterns, _PATTERNS_PATH
    _target_to_patterns = None
    _PATTERNS_PATH = path


def _safe_split(line: str, delimiter: str = ",") -> list[str]:
    result: list[str] = []
    literal = False
    escape = False
    startpos = 0
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"' and not escape:
            literal = not literal
        if not literal and ch == delimiter and not escape:
            result.append(line[startpos:i])
            startpos = i + 1
        escape = not escape if ch == "\\" else False
        i += 1
    result.append(line[startpos:i])
    return result


def _clean_column(col: str) -> str:
    if col.startswith('"') and col.endswith('"') and len(col) > 1:
        col = col[1:-1]
    col = col.replace('\\"', '"')
    col = col.replace("\\n", "\n")
    return col


def load_patterns() -> dict[str, list[tuple[str, str]]]:
    global _target_to_patterns
    if _target_to_patterns is not None:
        return _target_to_patterns

    _target_to_patterns = {}

    if _PATTERNS_PATH is not None:
        import pathlib

        path = pathlib.Path(_PATTERNS_PATH)
        f = path.open("r", encoding="utf-8")
    else:
        from importlib.resources import files

        f = files("circe.sqlrender").joinpath("replacementPatterns.csv").open("r", encoding="utf-8")

    try:
        first = True
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if first:
                first = False
                continue
            if not line:
                continue
            columns = _safe_split(line, ",")
            if len(columns) < 3:
                continue
            target = _clean_column(columns[0]).strip()
            pattern = _clean_column(columns[1])
            replacement = _clean_column(columns[2])
            pattern = pattern.replace("@", "@@")
            replacement = replacement.replace("@", "@@")
            _target_to_patterns.setdefault(target, []).append((pattern, replacement))
    finally:
        f.close()

    return _target_to_patterns


def get_supported_dialects() -> list[str]:
    patterns = load_patterns()
    return sorted(patterns.keys())
