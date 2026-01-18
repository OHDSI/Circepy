"""
Tests for real example cohorts - Markdown parity.
"""

from circe.api import cohort_expression_from_json, cohort_print_friendly
from pathlib import Path
from typing import Optional, Tuple, Dict
import pytest
import re
from difflib import unified_diff
import textwrap
import random

# Test cohort files
COHORTS_DIR = Path(__file__).parent / 'cohorts'
REFERENCE_DIR = COHORTS_DIR / 'reference_outputs'

# Cache for generated markdown to avoid redundant work
_MARKDOWN_CACHE: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

def get_target_cohort_files(config):
    """Discover cohort files based on configuration."""
    if not COHORTS_DIR.exists():
        return []
        
    all_files = sorted([f.name for f in COHORTS_DIR.glob('*.json')])
    
    cohort_filter = config.getoption("--cohort-filter")
    sample_cohorts = config.getoption("--sample-cohorts")
    
    if cohort_filter:
        targets = [f.strip() for f in cohort_filter.split(',')]
        return targets
        
    if sample_cohorts:
        return random.sample(all_files, min(len(all_files), 10))
        
    return all_files

def pytest_generate_tests(metafunc):
    """Dynamic parameterization for cohort tests."""
    if "cohort_name" in metafunc.fixturenames:
        cohort_files = get_target_cohort_files(metafunc.config)
        params = []
        for f in cohort_files:
            params.append(f)
        metafunc.parametrize("cohort_name", params)

@pytest.fixture(scope="module")
def shared_markdown_cache():
    return _MARKDOWN_CACHE

def get_generated_markdown(cohort_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get generated markdown for a cohort, using cache if available.
    """
    if cohort_name in _MARKDOWN_CACHE:
        return _MARKDOWN_CACHE[cohort_name]
        
    cohort_file = COHORTS_DIR / cohort_name
    markdown = None
    error = None

    try:
        # Read and parse JSON
        json_str = cohort_file.read_text()
        expression = cohort_expression_from_json(json_str)

        # Generate Markdown
        try:
            markdown = cohort_print_friendly(expression)
        except Exception as e:
            error = f"Markdown generation failed: {str(e)}"

    except Exception as e:
        error = f"JSON parsing failed: {str(e)}"

    _MARKDOWN_CACHE[cohort_name] = (markdown, error)
    return markdown, error

def get_reference_markdown(cohort_name: str) -> Optional[str]:
    """Get pre-generated reference Markdown from R/Java implementation."""
    ref_file = REFERENCE_DIR / cohort_name.replace('.json', '.md')
    if ref_file.exists():
        return ref_file.read_text()
    return None

def normalize_markdown(text: str) -> str:
    """
    Normalize markdown for comparison - removes ALL formatting differences.
    """
    # Convert to lowercase for case-insensitive comparison
    text = text.lower()
    lines = text.split('\n')
    normalized = []
    skip_section = False
    
    for line in lines:
        line = line.strip()
        
        # Skip title and description sections (Python adds these, R doesn't)
        if line.startswith('# ') and not line.startswith('###'):
            skip_section = True
            continue
        if line.startswith('## ') and not line.startswith('###'):
            skip_section = True
            continue
        if skip_section and line.startswith('###'):
            skip_section = False
        if skip_section:
            continue
        
        # Skip empty lines
        if not line:
            continue
        
        # Normalize whitespace - collapse multiple spaces to single space
        line = ' '.join(line.split())
        normalized.append(line)
    
    # Join all lines with single space to ignore line break differences
    result = ' '.join(normalized)
    
    # Normalize some common markdown patterns
    # Normalize bullet points - spaces around * or -
    result = re.sub(r'\s*\*\s*', '* ', result)
    result = re.sub(r'\s*-\s*', '- ', result)
    # Normalize heading markers
    result = re.sub(r'\s*###\s*', '### ', result)
    result = re.sub(r'\s*##\s*', '## ', result)
    result = re.sub(r'\s*#\s*', '# ', result)
    
    return result.strip()

def compare_markdown_outputs(python_output: str, reference_output: str) -> dict:
    """
    Compare Python markdown with reference output.
    """
    py_normalized = normalize_markdown(python_output)
    ref_normalized = normalize_markdown(reference_output)
    
    is_identical = py_normalized == ref_normalized
    
    # Since normalization creates single-line strings, split them into chunks for readable diff
    if is_identical:
        diff = []
    else:
        # Break normalized output into chunks (every 100 chars) for diff display
        def chunk_string(s, size=100):
            return [s[i:i+size] for i in range(0, len(s), size)]
        
        py_chunks = chunk_string(py_normalized)
        ref_chunks = chunk_string(ref_normalized)
        
        diff = list(unified_diff(
            ref_chunks,
            py_chunks,
            fromfile='Reference (R/Java)',
            tofile='Python',
            lineterm='',
            n=2
        ))
    
    return {
        'is_identical': is_identical,
        'python_lines': len(python_output.splitlines()),
        'reference_lines': len(reference_output.splitlines()),
        'diff': diff[:50],
    }

def analyze_markdown_differences(py_md: str, ref_md: str) -> list:
    """
    Analyze Markdown differences and identify potential issues.
    """
    issues = []
    
    # Check for "Unknown criteria type" errors
    if 'unknown criteria type' in py_md.lower():
        matches = re.findall(r'unknown criteria type[:\s]+(\w+)', py_md.lower())
        for match in matches:
            issues.append(f"Unknown criteria type: {match} - deserialization issue")
    
    # Check for missing sections
    sections = [
        ('### Cohort Entry Events', 'Cohort Entry Events section'),
        ('### Inclusion Criteria', 'Inclusion Criteria section'),
        ('### Cohort Exit', 'Cohort Exit section'),
        ('### Cohort Eras', 'Cohort Eras section'),
    ]
    
    py_normalized = normalize_markdown(py_md)
    
    for pattern, name in sections:
        if pattern not in py_normalized:
            pass

    return issues

def test_markdown_generation_produces_output(cohort_name):
    """
    Test that Python generates Markdown without crashing.
    """
    markdown, error = get_generated_markdown(cohort_name)
    
    if error:
        pytest.fail(f"Markdown generation error for {cohort_name}: {error}")
    
    assert markdown is not None, f"No Markdown generated for {cohort_name}"

def test_markdown_has_no_unknown_types(cohort_name):
    """
    Test that Markdown doesn't contain "Unknown criteria type" errors.
    """
    markdown, error = get_generated_markdown(cohort_name)
    if error or markdown is None:
        pytest.skip(f"Markdown generation failed: {error}")
    
    # Check for unknown type errors
    unknown_pattern = re.compile(r'unknown criteria type', re.IGNORECASE)
    matches = unknown_pattern.findall(markdown)
    
    if matches:
        lines_with_unknown = [line for line in markdown.split('\n') if 'unknown' in line.lower()]
        pytest.fail(
            f"Markdown contains 'Unknown criteria type' for {cohort_name}\n\n"
            f"Lines with unknown types:\n" +
            "\n".join(f"  {line}" for line in lines_with_unknown)
        )

def test_markdown_matches_reference(cohort_name):
    """
    Test that Python Markdown matches the reference R/Java Markdown.
    """
    markdown, error = get_generated_markdown(cohort_name)
    if error or markdown is None:
        pytest.fail(f"Markdown generation failed: {error}")
    
    ref_md = get_reference_markdown(cohort_name)
    if ref_md is None:
        pytest.skip(f"No reference Markdown for {cohort_name}")
    
    comparison = compare_markdown_outputs(markdown, ref_md)
    
    if not comparison['is_identical']:
        issues = analyze_markdown_differences(markdown, ref_md)
        diff_preview = '\n'.join(comparison['diff'][:30])
        
        pytest.fail(
            f"Markdown does not match reference for {cohort_name}\n\n"
            f"Summary:\n"
            f"  Python lines: {comparison['python_lines']}, Reference lines: {comparison['reference_lines']}\n"
            f"Issues found:\n" +
            ("\n".join(f"  - {issue}" for issue in issues) if issues else "  (no specific issues identified)") +
            f"\n\nFirst 30 lines of diff:\n{diff_preview}"
        )

