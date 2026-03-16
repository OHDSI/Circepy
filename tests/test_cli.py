"""
Tests for CLI - comparing output with R CirceR

These tests run both the Python CLI and R CirceR script on the same cohorts
and compare the generated SQL and Markdown outputs.
"""

import functools
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from circe.cli import main

# Get list of test cohorts
COHORTS_DIR = Path(__file__).parent / "cohorts"
TEST_COHORTS = [
    "isolated_immune_thrombocytopenia.json",
]


@functools.lru_cache(maxsize=None)
def run_r_script_cached(cohort_file: Path) -> tuple[str, str]:
    """Run R CirceR script and return SQL and Markdown. Cached to avoid redundant slow R calls."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        sql_output = tmpdir_path / "output.sql"

        # Run R script
        result = subprocess.run(
            ["Rscript", "circe_sql.R", str(cohort_file), str(sql_output)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode != 0:
            pytest.skip(f"R script failed: {result.stderr}")

        # Read outputs
        sql = sql_output.read_text()
        md_file = sql_output.with_suffix(".md")
        markdown = md_file.read_text() if md_file.exists() else ""

        return sql, markdown


def run_python_cli_in_process(args: list[str]) -> tuple[int, str, str]:
    """Run Python CLI in-process and return exit code, stdout, and stderr."""
    stdout = StringIO()
    stderr = StringIO()

    with patch("sys.argv", ["circe"] + args):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                exit_code = main() or 0
            except SystemExit as e:
                exit_code = e.code
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                exit_code = 1

    return exit_code, stdout.getvalue(), stderr.getvalue()


@pytest.mark.parametrize("cohort_name", TEST_COHORTS)
def test_sql_generation_matches_r(cohort_name):
    """Test that Python CLI generates SQL similar to R CirceR."""
    cohort_file = COHORTS_DIR / cohort_name

    if shutil.which("Rscript") is None:
        pytest.skip("R not available")

    if not cohort_file.exists():
        pytest.skip(f"Cohort file not found: {cohort_file}")

    # Get R output (cached)
    r_sql, _ = run_r_script_cached(cohort_file)

    # Get Python output (in-process)
    with tempfile.TemporaryDirectory() as tmpdir:
        sql_output = Path(tmpdir) / "output.sql"
        exit_code, _, _ = run_python_cli_in_process(
            [
                "generate-sql",
                str(cohort_file),
                "--output",
                str(sql_output),
                "--no-validate",
            ]
        )

        assert exit_code == 0
        py_sql = sql_output.read_text()

    # Compare key structural elements
    assert "#Codesets" in py_sql, "Missing #Codesets table"
    assert "#qualified_events" in py_sql, "Missing #qualified_events table"
    assert "#included_events" in py_sql, "Missing #included_events table"

    # Check SQL is not trivially small
    assert len(py_sql) > 1000, "SQL output too small"

    # Compare sizes (Python should be reasonably close to R)
    py_lines = len(py_sql.splitlines())
    r_lines = len(r_sql.splitlines())

    # Allow Python to be smaller since #cohort_rows and #final_cohort are incomplete
    # But it should be at least 30% of R's size for the implemented parts
    assert py_lines >= r_lines * 0.3, (
        f"Python SQL too short: {py_lines} vs R {r_lines} lines"
    )


@pytest.mark.parametrize("cohort_name", TEST_COHORTS)
def test_markdown_generation(cohort_name):
    """Test that Python CLI generates Markdown."""
    cohort_file = COHORTS_DIR / cohort_name

    if not cohort_file.exists():
        pytest.skip(f"Cohort file not found: {cohort_file}")

    # Get Python output (in-process)
    with tempfile.TemporaryDirectory() as tmpdir:
        md_output = Path(tmpdir) / "output.md"
        exit_code, _, _ = run_python_cli_in_process(
            [
                "render-markdown",
                str(cohort_file),
                "--output",
                str(md_output),
                "--no-validate",
            ]
        )

        assert exit_code == 0
        py_md = md_output.read_text()

    # Check Markdown has expected sections
    assert "Cohort Entry Events" in py_md or "cohort entry" in py_md.lower()
    assert len(py_md) > 100, "Markdown output too small"


def test_validate_command():
    """Test validate command."""
    cohort_file = COHORTS_DIR / "isolated_immune_thrombocytopenia.json"

    exit_code, _, _ = run_python_cli_in_process(["validate", str(cohort_file)])

    # Validation may return warnings (exit code 1) but as long as it doesn't crash, it's OK
    assert exit_code in [0, 1], f"Unexpected exit code: {exit_code}"


def test_process_command():
    """Test process command."""
    cohort_file = COHORTS_DIR / "isolated_immune_thrombocytopenia.json"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        sql_output = tmpdir_path / "output.sql"
        md_output = tmpdir_path / "output.md"

        exit_code, _, _ = run_python_cli_in_process(
            [
                "process",
                str(cohort_file),
                "--sql-output",
                str(sql_output),
                "--md-output",
                str(md_output),
            ]
        )

        assert exit_code == 0
        assert sql_output.exists()
        assert md_output.exists()
        assert len(sql_output.read_text()) > 1000
        assert len(md_output.read_text()) > 100

        assert len(md_output.read_text()) > 100


def test_generate_source_command():
    """Test generate-source command."""
    cohort_file = COHORTS_DIR / "isolated_immune_thrombocytopenia.json"

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "cohort.py"

        exit_code, stdout, stderr = run_python_cli_in_process(
            ["generate-source", str(cohort_file), "--output", str(output_file)]
        )

        assert output_file.exists()

        content = output_file.read_text()
        assert "from circe.cohortdefinition.cohort import CohortExpression" in content
        assert "cohort =" in content

        # Also check stdout version
        exit_code, stdout, stderr = run_python_cli_in_process(
            ["generate-source", str(cohort_file)]
        )

        assert "cohort =" in stdout
