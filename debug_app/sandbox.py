"""
Restricted Python Sandbox for Cohort Builder Code Execution.

This module provides a safe execution environment that ONLY allows
circe.cohort_builder imports and requires a 'cohort' variable output.
"""

import re
from typing import Any


def validate_imports(code: str) -> tuple[bool, str]:
    """
    Validate that code only imports from allowed circe modules.

    Returns:
        (is_valid, error_message)
    """
    # Find all import statements
    import_pattern = r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))"

    allowed_modules = {
        "circe.cohort_builder",
        "circe.vocabulary",
    }

    for line in code.split("\n"):
        match = re.match(import_pattern, line)
        if match:
            module = match.group(1) or match.group(2)
            # Check if module or its parent is allowed
            if not any(module.startswith(allowed) for allowed in allowed_modules):
                return (
                    False,
                    f"Import '{module}' is not allowed. Only 'circe.cohort_builder' and 'circe.vocabulary' imports are permitted.",
                )

    return True, ""


def execute_cohort_code(code: str) -> dict[str, Any]:
    """
    Execute Python code with strict cohort builder restrictions.

    The code must:
    1. Only import from circe.cohort_builder and circe.vocabulary
    2. Define a 'cohort' variable containing a CohortExpression

    Args:
        code: Python source code to execute

    Returns:
        dict with keys:
            - cohort_expression: The built CohortExpression object
            - json: JSON representation
            - sql: Generated SQL
            - markdown: Print-friendly markdown
            - python_code: Generated Python code
            - error: Error message if execution failed
    """
    # Validate imports first
    is_valid, error_msg = validate_imports(code)
    if not is_valid:
        return {"error": error_msg}

    # Create restricted globals - only allow safe circe imports
    restricted_globals = {
        "__builtins__": {
            # Only safe built-ins
            "True": True,
            "False": False,
            "None": None,
            "int": int,
            "float": float,
            "str": str,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "min": min,
            "max": max,
            "sum": sum,
            "sorted": sorted,
            "print": print,  # Allow print for debugging
        }
    }

    local_scope = {}

    try:
        # Execute the code
        exec(code, restricted_globals, local_scope)

        # Verify 'cohort' variable exists
        if "cohort" not in local_scope:
            return {
                "error": "Code must define a 'cohort' variable. Example:\n\n"
                "from circe.cohort_builder import CohortBuilder\n"
                "cohort = CohortBuilder('My Cohort').with_condition(1).build()"
            }

        cohort_expression = local_scope["cohort"]

        # Import circe modules for processing (safe to do here)
        import json

        from circe.api import build_cohort_query, cohort_print_friendly
        from circe.cohortdefinition import BuildExpressionQueryOptions
        from circe.cohortdefinition.code_generator import to_python_code

        # Generate outputs
        options = BuildExpressionQueryOptions()
        options.generate_stats = True

        sql = build_cohort_query(cohort_expression, options)
        markdown = cohort_print_friendly(cohort_expression)
        python_code = to_python_code(cohort_expression)

        # Serialize to JSON
        json_output = json.dumps(cohort_expression.model_dump(exclude_none=True, by_alias=True), indent=2)

        return {
            "cohort_expression": cohort_expression,
            "json": json_output,
            "sql": sql,
            "markdown": markdown,
            "python_code": python_code,
            "error": None,
        }

    except SyntaxError as e:
        return {
            "error": f"Syntax Error: {e.msg} at line {e.lineno}\n\nCheck your Python syntax and try again."
        }
    except ImportError as e:
        return {
            "error": f"Import Error: {str(e)}\n\nOnly imports from 'circe.cohort_builder' and 'circe.vocabulary' are allowed."
        }
    except AttributeError as e:
        return {
            "error": f"Attribute Error: {str(e)}\n\nCheck the fluent API documentation for correct method names."
        }
    except Exception as e:
        import traceback

        return {"error": f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"}


# Example templates for users
EXAMPLE_TEMPLATES = {
    "simple": """from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("Simple Cohort")
    .with_condition(1)
    .build()
)""",
    "with_criteria": """from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("Cohort with Criteria")
    .with_condition(1)
    .first_occurrence()
    .min_age(18)
    .require_drug(2).anytime_after()
    .exclude_procedure(3).within_days_before(30)
    .build()
)""",
    "grouped_criteria": """from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("Grouped Criteria Cohort")
    .with_condition(1)
    .any_of()
        .require_drug(2).anytime_after()
        .require_drug(3).anytime_after()
    .end_group()
    .build()
)""",
    "demographics": """from circe.cohort_builder import CohortBuilder

cohort = (
    CohortBuilder("Demographics Cohort")
    .with_condition(1)
    .first_occurrence()
    .min_age(18)
    .max_age(65)
    .require_gender(8507)  # Male
    .require_race(8516)    # Black or African American
    .build()
)""",
}
