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

def _quote_value(val: Any) -> str:
    """Wrap strings in quotes for direct substitution into SQL, otherwise convert to string."""
    if isinstance(val, str):
        # Escape single quotes within the string
        escaped_val = val.replace("'", "''")
        return f"'{escaped_val}'"
    if val is None:
        return "NULL"
    return str(val)

def render_sql(template: str, params: Dict[str, Any]) -> str:
    """Render an OHDSI SQL template by resolving variables and conditional blocks.
    
    This function handles:
    1.  ``@variable``: Replaced by ``params['variable']``.
    2.  ``{cond}?{true_block}:{false_block}``: Conditional inclusion.
    """
    if template is None:
        return ""

    # 1. Handle variables
    def var_replacer(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in params:
            return _quote_value(params[var_name])
        return f"@{var_name}"  # Keep as is if not provided

    rendered = re.sub(r"@([A-Za-z_][A-Za-z0-9_]*)", var_replacer, template)

    # 2. Handle conditional blocks: {cond}?{true_block}:{false_block}
    # We use a manual parser to handle nested braces correctly.
    def resolve_blocks(text: str) -> str:
        # Find the first ?{ occurring
        while True:
            match = re.search(r"\{([^?}]*)\}\?\{", text)
            if not match:
                break
            
            start_bracket = match.start()
            # match.group(1) is the condition
            cond_str = match.group(1).strip()
            
            # Find the true block (starts after the ?{)
            true_start = match.end()
            
            # Find the matching } for the true block
            true_end = -1
            balance = 1
            for i in range(true_start, len(text)):
                if text[i] == "{":
                    balance += 1
                elif text[i] == "}":
                    balance -= 1
                    if balance == 0:
                        true_end = i
                        break
            
            if true_end == -1:
                # Malformed template
                break
            
            true_block = text[true_start:true_end]
            
            # Check for optional else block : {false_block}
            # Look ahead for : {
            after_true = text[true_end+1:].lstrip()
            false_block = ""
            total_end = true_end + 1
            
            if after_true.startswith(":"):
                remaining = after_true[1:].lstrip()
                if remaining.startswith("{"):
                    # Find matching } for false block
                    false_start = text.find("{", true_end + 1) + 1
                    false_end = -1
                    balance = 1
                    for i in range(false_start, len(text)):
                        if text[i] == "{":
                            balance += 1
                        elif text[i] == "}":
                            balance -= 1
                            if balance == 0:
                                false_end = i
                                break
                    if false_end != -1:
                        false_block = text[false_start:false_end]
                        total_end = false_end + 1
            
            # Resolve condition
            res = _evaluate_condition(cond_str, params)
            replacement = true_block if res else false_block
            
            # Replace only THIS block instance
            text = text[:start_bracket] + replacement + text[total_end:]
            
        return text

    rendered = resolve_blocks(rendered)
    return rendered


def translate_sql(
    sql: str,
    target_dialect: str,
    source_dialect: str = "tsql",
    temp_emulation_schema: str = None,
    temp_emulation_prefix: str = None,
) -> str:
    """Translate a SQL string from ``source_dialect`` to ``target_dialect``.

    The base dialect is assumed to be MS SQL Server (T-SQL).
    Supports temp table emulation if ``temp_emulation_schema`` is provided.
    """
    # 1. Remove comments as they can cause issues during parsing/translation
    # Remove single line comments
    sql = re.sub(r"--.*", "", sql)
    # Remove multi-line comments
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)

    # 2. Strip OHDSI-specific commands that sqlglot might struggle with
    # These are mostly performance hints for SQL Server or PDW
    sql = re.sub(r"(?i)UPDATE\s+STATISTICS\s+[^;]+;", "", sql)
    sql = re.sub(r"(?i)ANALYZE\s+[^;]+;", "", sql)
    sql = re.sub(r"(?i)VACUUM\s+[^;]+;", "", sql)
    
    # Remove lonely semicolons that might be left behind
    sql = re.sub(r";\s*;", ";", sql)

    try:
        # Normalize dialect names for comparison
        s_norm = sqlglot.Dialect.get_or_raise(source_dialect)
        try:
            t_norm = sqlglot.Dialect.get_or_raise(target_dialect)
        except Exception:
            t_norm = None

        # Short-circuit if same dialect and no emulation requested
        if t_norm and s_norm == t_norm and not temp_emulation_schema:
            return sql

        expressions = sqlglot.parse(sql, read=source_dialect)

        if temp_emulation_schema:
            import random
            import string

            if not temp_emulation_prefix:
                # Generate a random prefix for this set of statements
                rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
                temp_emulation_prefix = f"tmp_{rand}_"

            for expression in expressions:
                if not expression:
                    continue

                # 1. Remove TemporaryProperty from CREATE statements
                if isinstance(expression, exp.Create):
                    properties = expression.args.get("properties")
                    if properties:
                        properties.set(
                            "expressions",
                            [
                                p
                                for p in properties.expressions
                                if not isinstance(p, exp.TemporaryProperty)
                            ],
                        )

                # 2. Rewrite Table identifiers and schemas
                # MS SQL Server uses #temp syntax, which sqlglot parses as temporary tables.
                for table in expression.find_all(exp.Table):
                    if table.this and table.this.args.get("temporary"):
                        # Rewrite table name with prefix
                        table.this.set("this", f"{temp_emulation_prefix}{table.this.this}")
                        # Remove temporary flag from identifier
                        table.this.set("temporary", False)
                        # Set schema to emulation schema
                        table.set("db", exp.to_identifier(temp_emulation_schema))

        # Generate translated SQL for each expression, separated by semicolons
        sql_out = ";\n\n".join(
            expression.sql(dialect=target_dialect)
            for expression in expressions
            if expression
        )
        if sql_out and not sql_out.endswith(";"):
            sql_out += ";"

        return sql_out
    except Exception as exc:
        raise ValueError(f"Failed to translate SQL to '{target_dialect}': {exc}")
