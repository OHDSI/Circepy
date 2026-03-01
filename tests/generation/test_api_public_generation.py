from __future__ import annotations

import circe.api as api


def test_generation_and_subset_api_exports_present():
    assert hasattr(api, "create_generation_tables")
    assert hasattr(api, "generate_cohort")
    assert hasattr(api, "generate_cohort_set")
    assert hasattr(api, "get_generated_cohort_status")
    assert hasattr(api, "apply_subset")
    assert hasattr(api, "generate_subset")
    assert hasattr(api, "get_generated_cohort_counts")
    assert hasattr(api, "validate_generated_cohort")
