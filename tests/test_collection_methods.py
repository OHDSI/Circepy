"""
Tests for collection methods in the fluent cohort builder.

These methods allow simplified creation of grouped criteria without
manually managing .any_of()...end_group() chains.
"""

from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition.cohort import CohortExpression


def test_require_any_of_drugs():
    """Test require_any_of with drug IDs."""
    cohort = CohortBuilder("Test ANY Drugs").with_condition(1).require_any_of(drug_ids=[10, 11, 12]).build()

    assert isinstance(cohort, CohortExpression)
    assert len(cohort.inclusion_rules) == 1
    assert cohort.inclusion_rules[0].name == "Inclusion Criteria"
    assert cohort.inclusion_rules[0].expression.type == "ANY"
    assert len(cohort.inclusion_rules[0].expression.criteria_list) == 3

    # Verify all are drug criteria
    for cc in cohort.inclusion_rules[0].expression.criteria_list:
        assert cc.criteria.__class__.__name__ == "DrugExposure"


def test_require_any_of_mixed_domains():
    """Test require_any_of with multiple domain types."""
    cohort = (
        CohortBuilder("Test ANY Mixed")
        .with_condition(1)
        .require_any_of(condition_ids=[20, 21], drug_ids=[30], procedure_ids=[40, 41, 42])
        .build()
    )

    assert len(cohort.inclusion_rules) == 1
    assert cohort.inclusion_rules[0].expression.type == "ANY"
    # Should have 2 conditions + 1 drug + 3 procedures = 6 criteria
    assert len(cohort.inclusion_rules[0].expression.criteria_list) == 6


def test_require_all_of():
    """Test require_all_of creates ALL group."""
    cohort = CohortBuilder("Test ALL").with_drug(1).require_all_of(procedure_ids=[10, 11]).build()

    assert len(cohort.inclusion_rules) == 1
    assert cohort.inclusion_rules[0].expression.type == "ALL"
    assert len(cohort.inclusion_rules[0].expression.criteria_list) == 2


def test_require_at_least_of():
    """Test require_at_least_of with count parameter."""
    cohort = (
        CohortBuilder("Test AT_LEAST")
        .with_condition(1)
        .require_at_least_of(2, procedure_ids=[10, 11, 12, 13])
        .build()
    )

    assert len(cohort.inclusion_rules) == 1
    assert cohort.inclusion_rules[0].expression.type == "AT_LEAST"
    assert cohort.inclusion_rules[0].expression.count == 2
    assert len(cohort.inclusion_rules[0].expression.criteria_list) == 4


def test_exclude_any_of():
    """Test exclude_any_of creates exclusion criteria."""
    cohort = CohortBuilder("Test Exclusion").with_condition(1).exclude_any_of(drug_ids=[20, 21]).build()

    assert len(cohort.inclusion_rules) == 1
    # Verify exclusion criteria were created
    assert cohort.inclusion_rules[0].expression.type == "ANY"
    assert len(cohort.inclusion_rules[0].expression.criteria_list) == 2

    # Check that criteria have occurrence count of 0 (exclusion)
    for cc in cohort.inclusion_rules[0].expression.criteria_list:
        assert cc.occurrence.count == 0
        assert cc.occurrence.type == 0  # exactly 0


def test_collection_methods_chaining():
    """Test that collection methods can be chained together."""
    cohort = (
        CohortBuilder("Test Chaining")
        .with_condition(1)
        .require_any_of(drug_ids=[10, 11])
        .require_all_of(measurement_ids=[20, 21])
        .exclude_any_of(procedure_ids=[30])
        .build()
    )

    # Should have 3 groups in inclusion rules
    assert len(cohort.inclusion_rules) == 1
    assert cohort.inclusion_rules[0].expression.type == "ALL"
    assert len(cohort.inclusion_rules[0].expression.groups) == 3


def test_collection_with_named_rules():
    """Test collection methods with named inclusion rules."""
    cohort = (
        CohortBuilder("Test Named Rules")
        .with_condition(1)
        .begin_rule("Prior Medications")
        .require_any_of(drug_ids=[10, 11, 12])
        .begin_rule("Recent Procedures")
        .require_at_least_of(2, procedure_ids=[20, 21, 22, 23])
        .build()
    )

    assert len(cohort.inclusion_rules) == 2
    assert cohort.inclusion_rules[0].name == "Prior Medications"
    assert cohort.inclusion_rules[0].expression.type == "ANY"
    assert cohort.inclusion_rules[1].name == "Recent Procedures"
    assert cohort.inclusion_rules[1].expression.type == "AT_LEAST"


def test_empty_collection_ignored():
    """Test that collection methods with no IDs don't add empty groups."""
    cohort = (
        CohortBuilder("Test Empty")
        .with_condition(1)
        .require_any_of()  # No IDs provided
        .build()
    )

    # Should have no inclusion rules since no criteria were added
    assert cohort.inclusion_rules is None or len(cohort.inclusion_rules) == 0


def test_collection_with_observation_ids():
    """Test collection methods with observation concept sets."""
    cohort = (
        CohortBuilder("Test Observations").with_condition(1).require_any_of(observation_ids=[5, 6, 7]).build()
    )

    assert len(cohort.inclusion_rules) == 1
    assert cohort.inclusion_rules[0].expression.type == "ANY"
    assert len(cohort.inclusion_rules[0].expression.criteria_list) == 3

    for cc in cohort.inclusion_rules[0].expression.criteria_list:
        assert cc.criteria.__class__.__name__ == "Observation"


def test_collection_with_visit_ids():
    """Test collection methods with visit concept sets."""
    cohort = CohortBuilder("Test Visits").with_drug(1).require_all_of(visit_ids=[100, 101]).build()

    assert len(cohort.inclusion_rules) == 1
    assert cohort.inclusion_rules[0].expression.type == "ALL"
    assert len(cohort.inclusion_rules[0].expression.criteria_list) == 2

    for cc in cohort.inclusion_rules[0].expression.criteria_list:
        assert cc.criteria.__class__.__name__ == "VisitOccurrence"


def test_require_at_least_of_single_type():
    """Test at_least with a single domain type."""
    cohort = (
        CohortBuilder("Test AT_LEAST Single")
        .with_condition(1)
        .require_at_least_of(3, drug_ids=[10, 11, 12, 13, 14])
        .build()
    )

    assert cohort.inclusion_rules[0].expression.type == "AT_LEAST"
    assert cohort.inclusion_rules[0].expression.count == 3
    assert len(cohort.inclusion_rules[0].expression.criteria_list) == 5


def test_real_world_example():
    """Test a real-world clinical scenario using collection methods."""
    cohort = (
        CohortBuilder("Diabetes with Complications")
        .with_condition(1)  # Entry: Type 2 Diabetes
        .first_occurrence()
        .with_observation(prior_days=365)
        .require_age(18, 75)
        .begin_rule("Antidiabetic Medications")
        .require_any_of(drug_ids=[10, 11, 12])  # Metformin, Insulin, GLP-1
        .begin_rule("Diabetic Complications")
        .require_at_least_of(
            1,
            condition_ids=[20, 21, 22, 23],  # Retinopathy, Neuropathy, Nephropathy, CVD
        )
        .begin_rule("No Cancer History")
        .exclude_any_of(condition_ids=[30, 31, 32])  # Various cancers
        .build()
    )

    assert len(cohort.inclusion_rules) == 4  # Age + 3 named rules
    assert cohort.inclusion_rules[0].name == "Demographic Criteria"
    assert cohort.inclusion_rules[1].name == "Antidiabetic Medications"
    assert cohort.inclusion_rules[2].name == "Diabetic Complications"
    assert cohort.inclusion_rules[3].name == "No Cancer History"
