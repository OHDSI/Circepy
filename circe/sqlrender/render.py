import re
from typing import Any, Dict

import sqlglot
from sqlglot import exp

def _quote_value(value: Any) -> str:
    """Quote a Python value for safe SQL insertion.

    Handles strings, numbers, booleans, and None.
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    # Assume string-like
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"

def render_sql(template: str, params: Dict[str, Any], dialect: str = "spark") -> str:
    """Render a SQL template with ``@variable`` placeholders.

    Args:
        template: SQL string containing ``@variable`` placeholders.
        params: Mapping of variable names (without ``@``) to values.
        dialect: Target SQL dialect for quoting rules (currently used for
            ``sqlglot`` parsing only; quoting is generic.

    Returns:
        Rendered SQL string.
    """
    # Replace @var placeholders with quoted values
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name not in params:
            raise KeyError(f"Missing parameter for placeholder '@{var_name}'")
        return _quote_value(params[var_name])

    rendered = re.sub(r"@([A-Za-z_][A-Za-z0-9_]*)", replacer, template)
    # Parse with sqlglot to ensure valid syntax for the requested dialect
    try:
        parsed = sqlglot.parse_one(rendered, read=dialect)
        # Return the formatted SQL string for the same dialect
        return parsed.sql(dialect=dialect)
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"Failed to parse rendered SQL for dialect '{dialect}': {exc}")

def translate_sql(sql: str, target_dialect: str, source_dialect: str = "spark") -> str:
    """Translate a SQL string from ``source_dialect`` to ``target_dialect``.

    Uses ``sqlglot.transpile`` which returns a list of translated SQL strings.
    """
    try:
        translated = sqlglot.transpile(sql, read=source_dialect, write=target_dialect)
        return translated[0]
    except Exception as exc:
        raise ValueError(f"Failed to translate SQL to '{target_dialect}': {exc}")
