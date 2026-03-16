import os
import re
import sys
from pathlib import Path

# Ensure we can import circe
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from circe.api import (
    build_cohort_query,
    cohort_expression_from_json,
    cohort_print_friendly,
)
from circe.cohortdefinition import BuildExpressionQueryOptions
from circe.cohortdefinition.code_generator import to_python_code


def normalize_sql(sql: str) -> str:
    """
    Normalize SQL for comparison - removes ALL formatting differences.
    Returns a formatted multi-line string for readability.
    """
    if not sql:
        return ""

    # 1. Basic cleanup
    sql = sql.lower()
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # Remove /* comments */
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)  # Remove -- comments

    # 2. Circe-specific removals (legacy compat)
    sql = re.sub(r"\{[^}]*\}\?\{", "", sql)
    sql = re.sub(r"\}", " ", sql)
    sql = re.sub(
        r"--\s*the matching group.*?inclusion_rule_mask\s+=\s+power\(.*?\)\s*-\s*1\)\)\s*results",
        ") results",
        sql,
        flags=re.DOTALL,
    )
    sql = re.sub(
        r"where\s*\(mg\.inclusion_rule_mask\s*=\s*power\(cast\(2\s+as\s+bigint\),\s*0\)\s*-\s*1\)",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    # 3. Strip specific columns known to differ harmlessly
    sql = re.sub(r",o\.value_as_string", "", sql)
    sql = re.sub(r",o\.value_as_concept_id", "", sql)
    sql = re.sub(r",o\.unit_concept_id", "", sql)

    # 4. Canonicalize whitespace (flatten first)
    sql = sql.replace(",o.value_as_string", "")
    sql = sql.replace(",o.value_as_concept_id", "")
    sql = sql.replace(",o.unit_concept_id", "")
    sql = re.sub(r"\s+", " ", sql).strip()

    # 5. Re-format for readability (Multi-line)
    # Add newlines before major keywords
    keywords = [
        "select",
        "from",
        "inner join",
        "left join",
        "right join",
        "join",
        "where",
        "group by",
        "order by",
        "having",
        "limit",
        "union",
        "with",
        "intersect",
        "except",
    ]
    for kw in keywords:
        # Look for keyword preceded by space
        # We replace " keyword" with "\nkeyword"
        sql = re.sub(f"\\s({kw})\\s", "\n\\1 ", sql)

    # Consistency for SQL tokens
    sql = re.sub(r"\s*([(),=<>!]+)\s*", r"\1", sql)

    return sql.strip()


def normalize_markdown(text: str) -> str:
    """
    Normalize markdown for comparison.
    """
    if not text:
        return ""

    text = text.lower()
    lines = text.split("\n")
    normalized = []
    skip_section = False

    for line in lines:
        line = line.strip()

        # Skip title and description sections (they change often / aren't functional logic)
        if line.startswith("# ") and not line.startswith("###"):
            skip_section = True
            continue
        if line.startswith("## ") and not line.startswith("###"):
            skip_section = True
            continue
        if skip_section and line.startswith("###"):
            skip_section = False
        if skip_section:
            continue

        if not line:
            continue

        # Collapse internal whitespace of the line
        line = " ".join(line.split())
        normalized.append(line)

    # Join with newlines to preserve structure (readability)
    result = "\n".join(normalized)

    # Normalize common markers
    result = re.sub(r"\s*\*\s*", "* ", result)
    result = re.sub(r"\s*-\s*", "- ", result)
    result = re.sub(r"\s*###\s*", "### ", result)
    result = re.sub(r"\s*##\s*", "## ", result)
    result = re.sub(r"\s*#\s*", "# ", result)

    return result.strip()


def generate_from_json(json_str: str) -> dict:
    try:
        expression = cohort_expression_from_json(json_str)

        # SQL
        options = BuildExpressionQueryOptions()
        options.generate_stats = True
        sql = build_cohort_query(expression, options)

        # Markdown
        markdown = cohort_print_friendly(expression)

        # Python Code
        python_code = to_python_code(expression)

        return {
            "sql": sql,
            "markdown": markdown,
            "python_code": python_code,
            "normalized_sql": normalize_sql(sql),
            "normalized_markdown": normalize_markdown(markdown),
            "error": None,
        }
    except Exception as e:
        return {
            "sql": None,
            "markdown": None,
            "python_code": None,
            "normalized_sql": "",
            "normalized_markdown": "",
            "error": str(e),
        }


def execute_python_code(code: str) -> dict:
    try:
        local_scope = {}
        exec(code, {}, local_scope)

        if "cohort" not in local_scope:
            return {"error": "The executed code did not define a 'cohort' variable."}

        expression = local_scope["cohort"]

        # SQL
        options = BuildExpressionQueryOptions()
        options.generate_stats = True
        sql = build_cohort_query(expression, options)

        # Markdown
        markdown = cohort_print_friendly(expression)

        return {
            "sql": sql,
            "markdown": markdown,
            "normalized_sql": normalize_sql(sql),
            "normalized_markdown": normalize_markdown(markdown),
            "error": None,
        }
    except Exception as e:
        import traceback

        return {
            "sql": None,
            "markdown": None,
            "normalized_sql": "",
            "normalized_markdown": "",
            "error": f"{str(e)}\n{traceback.format_exc()}",
        }


def generate_reference_with_r(json_content: str) -> dict:
    """
    Uses the circe_sql.R script to generate reference SQL and Markdown via R.
    """
    import subprocess
    import tempfile

    r_script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "circe_sql.R")
    )

    if not os.path.exists(r_script_path):
        return {
            "error": f"R script not found at {r_script_path}",
            "sql": "",
            "markdown": "",
        }

    with tempfile.TemporaryDirectory() as tmpdirname:
        json_path = os.path.join(tmpdirname, "input.json")
        sql_path = os.path.join(tmpdirname, "output.sql")
        md_path = os.path.join(tmpdirname, "output.md")

        with open(json_path, "w") as f:
            f.write(json_content)

        try:
            subprocess.run(
                ["Rscript", r_script_path, json_path, sql_path],
                capture_output=True,
                text=True,
                check=True,
            )

            ref_sql = ""
            ref_md = ""

            if os.path.exists(sql_path):
                with open(sql_path) as f:
                    ref_sql = f.read()

            if os.path.exists(md_path):
                with open(md_path) as f:
                    ref_md = f.read()

            return {
                "sql": ref_sql,
                "markdown": ref_md,
                "normalized_sql": normalize_sql(ref_sql),
                "normalized_markdown": normalize_markdown(ref_md),
                "error": None,
            }

        except subprocess.CalledProcessError as e:
            return {
                "sql": "",
                "markdown": "",
                "normalized_sql": "",
                "normalized_markdown": "",
                "error": f"R execution failed:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}",
            }
            return {
                "sql": "",
                "markdown": "",
                "normalized_sql": "",
                "normalized_markdown": "",
                "error": f"Unexpected error running R: {str(e)}",
            }


def get_ai_explanation(
    ref_content: str, gen_content: str, type_label: str = "SQL"
) -> dict:
    """
    Uses Google GenAI to explain the differences between reference and generated content.
    """
    import hashlib
    import json
    import os

    # 1. Construct Prompt FIRST (so we can hash it)
    prompt = f"""
        You are an expert SQL and Database logic analyst.
        I have two versions of a {type_label} output.
        
        Version A (Reference/Correct):
        {ref_content}
        
        Version B (Generated/New):
        {gen_content}
        
        Task:
        1. Compare Version A and Version B.
        2. Identify functional differences (logic, values, table joins, flow).
        3. Ignore non-functional whitespace or formatting differences.
        4. Explain IF the differences matter functionally and WHY. 
        5. If they are functionally equivalent, explicitly state that.
        
        Concise explanation:
        """

    # 2. Check Cache
    try:
        cache_dir = Path(__file__).parent / ".gemini_cache"
        cache_dir.mkdir(exist_ok=True)

        # Hash the prompt
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cache_file = cache_dir / f"{prompt_hash}.json"

        if cache_file.exists():
            print(f"Cache hit for {prompt_hash}")
            with open(cache_file) as f:
                cached_data = json.load(f)
                return {"explanation": cached_data["explanation"], "error": None}
    except Exception as e:
        print(f"Cache check failed: {e}")

    # 3. Load Key & Libraries (only if not cached)
    try:
        from google import genai
    except ImportError:
        return {
            "error": "google-genai library not installed. Please pip install google-genai."
        }

    try:
        from dotenv import load_dotenv

        env_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", ".env")
        )
        load_dotenv(env_path, override=True)
    except ImportError:
        pass

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {
            "error": "GOOGLE_API_KEY environment variable not set. Please set it in a .env file or in your terminal."
        }

    # 4. Call API
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", contents=prompt
        )

        explanation = response.text

        # 5. Save to Cache
        try:
            with open(cache_file, "w") as f:
                json.dump(
                    {"explanation": explanation, "model": "gemini-2.5-flash-lite"}, f
                )
        except Exception as e:
            print(f"Failed to save cache: {e}")

        return {"explanation": explanation, "error": None}

    except Exception as e:
        return {"error": f"AI Generation failed: {str(e)}", "explanation": None}
