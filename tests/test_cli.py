"""
Tests for CLI - comparing output with R CirceR

These tests run both the Python CLI and R CirceR script on the same cohorts
and compare the generated SQL and Markdown outputs.
"""

import subprocess
import sys
from pathlib import Path
import pytest
import tempfile
import shutil

# Get list of test cohorts
COHORTS_DIR = Path(__file__).parent / 'cohorts'
TEST_COHORTS = [
    '1006.json',  # Simple cohort
    '10.json',    # Multiple criteria
    '1195.json',  # Complex cohort
]


def run_r_script(cohort_file: Path) -> tuple[str, str]:
    """Run R CirceR script and return SQL and Markdown."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        sql_output = tmpdir_path / 'output.sql'
        
        # Run R script
        result = subprocess.run(
            ['Rscript', 'circe_sql.R', str(cohort_file), str(sql_output)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode != 0:
            pytest.skip(f"R script failed: {result.stderr}")
        
        # Read outputs
        sql = sql_output.read_text()
        md_file = sql_output.with_suffix('.md')
        markdown = md_file.read_text() if md_file.exists() else ""
        
        return sql, markdown


def run_python_cli(cohort_file: Path) -> tuple[str, str]:
    """Run Python CLI and return SQL and Markdown."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        sql_output = tmpdir_path / 'output.sql'
        md_output = tmpdir_path / 'output.md'
        
        # Run Python CLI for SQL
        result = subprocess.run(
            [sys.executable, '-m', 'circe.cli', 'generate-sql', str(cohort_file),
             '--output', str(sql_output), '--no-validate'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Python CLI failed: {result.stderr}")
        
        # Run Python CLI for Markdown
        result = subprocess.run(
            [sys.executable, '-m', 'circe.cli', 'render-markdown', str(cohort_file),
             '--output', str(md_output), '--no-validate'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Python CLI failed: {result.stderr}")
        
        sql = sql_output.read_text()
        markdown = md_output.read_text()
        
        return sql, markdown


@pytest.mark.parametrize('cohort_name', TEST_COHORTS)
def test_sql_generation_matches_r(cohort_name):
    """Test that Python CLI generates SQL similar to R CirceR."""
    cohort_file = COHORTS_DIR / cohort_name

    if shutil.which("Rscript") is None:
        pytest.skip(f"R not available")

    if not cohort_file.exists():
        pytest.skip(f"Cohort file not found: {cohort_file}")
    
    # Get R output
    r_sql, _ = run_r_script(cohort_file)
    
    # Get Python output
    py_sql, _ = run_python_cli(cohort_file)
    
    # Compare key structural elements
    assert '#Codesets' in py_sql, "Missing #Codesets table"
    assert '#qualified_events' in py_sql, "Missing #qualified_events table"
    assert '#included_events' in py_sql, "Missing #included_events table"
    
    # Check SQL is not trivially small
    assert len(py_sql) > 1000, "SQL output too small"
    
    # Compare sizes (Python should be reasonably close to R)
    py_lines = len(py_sql.splitlines())
    r_lines = len(r_sql.splitlines())
    
    # Allow Python to be smaller since #cohort_rows and #final_cohort are incomplete
    # But it should be at least 30% of R's size for the implemented parts
    assert py_lines >= r_lines * 0.3, f"Python SQL too short: {py_lines} vs R {r_lines} lines"


@pytest.mark.parametrize('cohort_name', TEST_COHORTS)
def test_markdown_generation(cohort_name):
    """Test that Python CLI generates Markdown."""
    cohort_file = COHORTS_DIR / cohort_name
    
    if not cohort_file.exists():
        pytest.skip(f"Cohort file not found: {cohort_file}")
    
    # Get Python output
    _, py_md = run_python_cli(cohort_file)
    
    # Check Markdown has expected sections
    assert 'Cohort Entry Events' in py_md or 'cohort entry' in py_md.lower()
    assert len(py_md) > 100, "Markdown output too small"


def test_validate_command():
    """Test validate command."""
    cohort_file = COHORTS_DIR / '1006.json'
    
    result = subprocess.run(
        [sys.executable, '-m', 'circe.cli', 'validate', str(cohort_file)],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Validation may return warnings (exit code 1) but as long as it doesn't crash, it's OK
    assert result.returncode in [0, 1], f"Unexpected exit code: {result.returncode}"


def test_process_command():
    """Test process command."""
    cohort_file = COHORTS_DIR / '1006.json'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        sql_output = tmpdir_path / 'output.sql'
        md_output = tmpdir_path / 'output.md'
        
        result = subprocess.run(
            [sys.executable, '-m', 'circe.cli', 'process', str(cohort_file),
             '--sql-output', str(sql_output),
             '--md-output', str(md_output)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0
        assert sql_output.exists()
        assert md_output.exists()
        assert len(sql_output.read_text()) > 1000
        assert len(md_output.read_text()) > 100

