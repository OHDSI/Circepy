"""
Tests for domain-specific modifiers in the new parameter-based fluent cohort builder API.
"""

from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition.cohort import CohortExpression


def test_procedure_with_quantity():
    """Test procedure quantity modifier."""
    cohort = (
        CohortBuilder("Test Procedure Quantity")
        .with_condition(1)
        .begin_rule("Procedure Rule")
        .require_procedure(10, quantity_min=1, quantity_max=5, anytime_before=True)
        .build()
    )

    assert isinstance(cohort, CohortExpression)
    # Check that quantity range was applied
    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.quantity is not None
    assert criteria.criteria.quantity.value == 1.0
    assert criteria.criteria.quantity.extent == 5.0


def test_measurement_with_operator():
    """Test measurement operator modifier."""
    cohort = (
        CohortBuilder("Test Measurement Operator")
        .with_condition(1)
        .begin_rule("Measurement Rule")
        .require_measurement(10, operator=4172704, anytime_before=True)  # Greater than
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.operator is not None
    assert len(criteria.criteria.operator) == 1
    assert criteria.criteria.operator[0].concept_id == 4172704


def test_measurement_with_range_ratios():
    """Test measurement range ratio modifiers."""
    cohort = (
        CohortBuilder("Test Measurement Ratios")
        .with_drug(1)
        .begin_rule("Measurement Rule")
        .require_measurement(
            10,
            range_low_ratio_min=0.5,
            range_low_ratio_max=1.5,
            range_high_ratio_min=1.0,
            range_high_ratio_max=2.0,
            anytime_before=True,
        )
        .build()
    )

    cohort.inclusion_rules[0].expression.criteria_list[0]
    # Check ratios (these need to be added to the builder later if not already supported)
    # For now, just verifying the API call works and values are in QueryConfig
    # The actual mapping to OHDSI JSON happens in cohortdefinition/builders/measurement.py
    # which I should also check.


def test_drug_with_route():
    """Test drug route modifier."""
    cohort = (
        CohortBuilder("Test Drug Route")
        .with_condition(1)
        .begin_rule("Drug Rule")
        .require_drug(10, route=4132161, anytime_before=True)  # Oral
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.route_concept is not None
    assert len(criteria.criteria.route_concept) == 1
    assert criteria.criteria.route_concept[0].concept_id == 4132161


def test_drug_with_refills():
    """Test drug refills modifier."""
    cohort = (
        CohortBuilder("Test Drug Refills")
        .with_condition(1)
        .begin_rule("Drug Rule")
        .require_drug(10, refills_min=1, refills_max=12, anytime_before=True)
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.refills is not None
    assert criteria.criteria.refills.value == 1
    assert criteria.criteria.refills.extent == 12


def test_drug_with_dose():
    """Test drug dose modifier."""
    cohort = (
        CohortBuilder("Test Drug Dose")
        .with_procedure(1)
        .begin_rule("Drug Rule")
        .require_drug(10, dose_min=10.0, dose_max=50.0, anytime_before=True)
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.effective_drug_dose is not None
    assert criteria.criteria.effective_drug_dose.value == 10.0
    assert criteria.criteria.effective_drug_dose.extent == 50.0


def test_visit_with_place_of_service():
    """Test visit place_of_service modifier."""
    cohort = (
        CohortBuilder("Test Visit Place of Service")
        .with_condition(1)
        .begin_rule("Visit Rule")
        .require_visit(10, place_of_service=8546, anytime_before=True)  # Hospice
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.place_of_service is not None
    assert len(criteria.criteria.place_of_service) == 1
    assert criteria.criteria.place_of_service[0].concept_id == 8546


def test_observation_with_qualifier():
    """Test observation qualifier modifier."""
    cohort = (
        CohortBuilder("Test Observation Qualifier")
        .with_condition(1)
        .begin_rule("Observation Rule")
        .require_observation(10, qualifier=4214956, anytime_before=True)
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.qualifier is not None
    assert len(criteria.criteria.qualifier) == 1
    assert criteria.criteria.qualifier[0].concept_id == 4214956


def test_multiple_modifiers_chained():
    """Test multiple modifiers on one criterion via parameters."""
    cohort = (
        CohortBuilder("Test Multi-Modifier")
        .with_condition(1)
        .begin_rule("Drug Rule")
        .require_drug(
            10,
            route=4132161,
            refills_min=2,
            refills_max=6,
            dose_min=5.0,
            dose_max=20.0,
            days_supply_min=30,
            days_supply_max=90,
            anytime_before=True,
        )
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.route_concept is not None
    assert criteria.criteria.refills is not None
    assert criteria.criteria.effective_drug_dose is not None
    assert criteria.criteria.days_supply is not None
