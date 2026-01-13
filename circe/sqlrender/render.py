import re
from typing import Any, Dict

import sqlglot
from sqlglot import exp

def _evaluate_condition(condition: str, params: Dict[str, Any]) -> bool:
    """Evaluate a simple OHDSI-style condition.
    
    Supports variables (@target), comparisons (==, !=, <, >, <=, >=),
    and logical operators (&, |).
    """
    # Replace @vars with their values in the condition string
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        val = params.get(var_name, 0)
        # Wrap strings in quotes for eval
        if isinstance(val, str):
            return f"'{val}'"
        return str(val)

    cond_eval = re.sub(r"@([A-Za-z_][A-Za-z0-9_]*)", replacer, condition)
    
    # Replace & with 'and', | with 'or'
    cond_eval = cond_eval.replace('&', ' and ').replace('|', ' or ')
    
    try:
        # Use a very limited scope for eval
        return bool(eval(cond_eval, {"__builtins__": {}}, {}))
    except Exception:
        # Fallback for complex things we can't eval easily - assume False or try simple strings
        return False

def render_sql(template: str, params: Dict[str, Any], dialect: str = "tsql") -> str:
    """Render a SQL template with ``@variable`` placeholders and conditional blocks.

    Args:
        template: SQL string containing ``@variable`` placeholders and ``{cond}?{if_true}:{if_false}`` blocks.
        params: Mapping of variable names (without ``@``) to values.
        dialect: Target SQL dialect for formatting.

    Returns:
        Rendered SQL string.
    """
    # 1. Handle conditional blocks: {cond}?{true_block}:{false_block}
    # This regex handles optional else block and some nesting (simple)
    pattern = re.compile(r"\{([^?}]*)\}\?\{([^}]*)\}(?:\s*:\s*\{([^}]*)\})?", re.DOTALL)
    
    def cond_replacer(match: re.Match) -> str:
        condition = match.group(1).strip()
        true_block = match.group(2)
        false_block = match.group(3) or ""
        
        if _evaluate_condition(condition, params):
            return true_block
        else:
            return false_block

    # Iterate to handle nested blocks if any (max 5 levels)
    rendered = template
    for _ in range(5):
        new_rendered = pattern.sub(cond_replacer, rendered)
        if new_rendered == rendered:
            break
        rendered = new_rendered

    # 2. Replace @var placeholders with raw values (simple string substitution)
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name not in params:
            # For OHDSI, we might want to keep the variable if it's meant for later rendering,
            # but usually it's an error if we're doing final rendering.
            # Let's keep it if not provided to allow multi-stage rendering.
            return match.group(0)
        val = params[var_name]
        return str(val) if val is not None else ""

    rendered = re.sub(r"@([A-Za-z_][A-Za-z0-9_]*)", replacer, rendered)
    
    # Attempt to format with sqlglot, but fall back to raw if it fails
    try:
        return sqlglot.transpile(rendered, read=dialect, write=dialect)[0]
    except Exception:
        return rendered

def translate_sql(sql: str, target_dialect: str, source_dialect: str = "tsql") -> str:
    """Translate a SQL string from ``source_dialect`` to ``target_dialect``.

    Uses ``sqlglot.transpile`` which returns a list of translated SQL strings.
    """
    try:
        # transpile handles dialect conversion. 
        # For OHDSI SQL, 'tsql' is a good source dialect for '#temp' tables and '@var' passing.
        translated = sqlglot.transpile(sql, read=source_dialect, write=target_dialect, identify=True)
        return translated[0]
    except Exception as exc:
        raise ValueError(f"Failed to translate SQL to '{target_dialect}': {exc}")
