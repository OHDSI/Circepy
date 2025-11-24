"""Test cases for markdown generation parity with R CirceR.

This module contains test cases generated from comparing Python and R markdown outputs
across multiple cohorts. These tests ensure consistent behavior.
"""

import json
import pytest
from pathlib import Path
from circe.api import cohort_expression_from_json, cohort_print_friendly


# Load test cases from comparison results
COMPARISON_RESULTS_FILE = Path(__file__).parent.parent / "markdown_comparison_results.json"


def load_test_cases():
    """Load test cases from comparison results."""
    if not COMPARISON_RESULTS_FILE.exists():
        pytest.skip(f"Comparison results file not found: {COMPARISON_RESULTS_FILE}")
    
    with open(COMPARISON_RESULTS_FILE, 'r') as f:
        data = json.load(f)
    
    # Return successful cohorts (those that generated markdown from both Python and R)
    return [
        r for r in data.get('successful_results', [])
        if 'error' not in r
    ]


@pytest.mark.parametrize("test_case", load_test_cases())
def test_markdown_generation(test_case):
    """Test that Python markdown generation works for each cohort."""
    json_file = Path(test_case['file'])
    
    if not json_file.exists():
        pytest.skip(f"JSON file not found: {json_file}")
    
    # Load and generate markdown
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    
    cohort = cohort_expression_from_json(json.dumps(json_data))
    python_md = cohort_print_friendly(cohort, include_concept_sets=False)
    
    # Basic checks
    assert python_md is not None
    assert len(python_md) > 0
    
    # Check that all sections are present if R had them
    sections = test_case.get('sections', {})
    python_md_lower = python_md.lower()
    
    for section_name, (r_has, _) in sections.items():
        if r_has:
            # R has this section, Python should too
            section_keywords = {
                'Cohort Entry Events': 'cohort entry events',
                'Inclusion Criteria': 'inclusion criteria',
                'Cohort Exit': 'cohort exit',
                'Cohort Eras': 'cohort eras',
                'Additional Criteria': 'restrict entry events',
            }
            keyword = section_keywords.get(section_name)
            if keyword:
                assert keyword in python_md_lower, \
                    f"Missing section '{section_name}' in {test_case['name']}"


@pytest.mark.parametrize("test_case", load_test_cases())
def test_no_unknown_criteria_types(test_case):
    """Test that no 'Unknown criteria type' errors appear in markdown."""
    json_file = Path(test_case['file'])
    
    if not json_file.exists():
        pytest.skip(f"JSON file not found: {json_file}")
    
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    
    cohort = cohort_expression_from_json(json.dumps(json_data))
    python_md = cohort_print_friendly(cohort, include_concept_sets=False)
    
    assert "Unknown criteria type" not in python_md, \
        f"Found 'Unknown criteria type' in {test_case['name']}"


def test_specific_cohorts():
    """Test specific cohorts that are known to have issues."""
    test_cohorts = [
        'tests/cohorts/1299.json',  # ProcedureOccurrence deserialization
        'tests/cohorts/1.json',  # Known working cohort
        'tests/cohorts/1006.json',  # Known working cohort
        'tests/cohorts/22.json',  # Known working cohort
        'tests/cohorts/1006.json',  # Known working cohort
        'tests/cohorts/2.json',     # Known working cohort
        'tests/cohorts/730.json',     # Known working cohort
        'complex_diabetes_cohort.json',  # Complex example
    ]
    
    for cohort_path in test_cohorts:
        json_file = Path(__file__).parent.parent / cohort_path
        if not json_file.exists():
            continue
        
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        
        cohort = cohort_expression_from_json(json.dumps(json_data))
        python_md = cohort_print_friendly(cohort, include_concept_sets=False)
        
        # Should not have unknown criteria types
        assert "Unknown criteria type" not in python_md, \
            f"Found 'Unknown criteria type' in {cohort_path}"
        
        # Should have basic structure
        assert "Cohort Entry Events" in python_md or "cohort entry" in python_md.lower(), \
            f"Missing cohort entry section in {cohort_path}"

