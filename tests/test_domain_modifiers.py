"""
Tests for Phase 2 domain-specific modifiers in the fluent cohort builder.
"""

import pytest
from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition.cohort import CohortExpression


def test_procedure_with_quantity():
    """Test procedure quantity modifier."""
    cohort = (
        CohortBuilder("Test Procedure Quantity")
        .with_condition(1)
        .begin_rule("Procedure Rule")
        .require_procedure(10).with_quantity(min_qty=1, max_qty=5).anytime_before()
        .build()
    )
    
    assert isinstance(cohort, CohortExpression)
    # Check that quantity range was applied (rule 0 is "Procedure Rule")
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
        .require_measurement(10).with_operator(4172704).anytime_before()  # Greater than
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
        .require_measurement(10)\
            .with_range_low_ratio(min_ratio=0.5, max_ratio=1.5)\
            .with_range_high_ratio(min_ratio=1.0, max_ratio=2.0)\
            .anytime_before()
        .build()
    )
    
    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.range_low_ratio is not None
    assert criteria.criteria.range_low_ratio.value == 0.5
    assert criteria.criteria.range_low_ratio.extent == 1.5
    assert criteria.criteria.range_high_ratio is not None
    assert criteria.criteria.range_high_ratio.value == 1.0
    assert criteria.criteria.range_high_ratio.extent == 2.0


def test_drug_with_route():
    """Test drug route modifier."""
    cohort = (
        CohortBuilder("Test Drug Route")
        .with_condition(1)
        .begin_rule("Drug Rule")
        .require_drug(10).with_route(4132161).anytime_before()  # Oral
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
        .require_drug(10).with_refills(min_refills=1, max_refills=12).anytime_before()
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
        .require_drug(10).with_dose(min_dose=10.0, max_dose=50.0).anytime_before()
        .build()
    )
    
    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.effective_drug_dose is not None
    assert criteria.criteria.effective_drug_dose.value == 10.0
    assert criteria.criteria.effective_drug_dose.extent == 50.0


def test_visit_with_admitted_from():
    """Test visit admitted_from modifier."""
    cohort = (
        CohortBuilder("Test Visit Admitted From")
        .with_condition(1)
        .begin_rule("Visit Rule")
        .require_visit(10).with_admitted_from(8715).anytime_before()  # Emergency Room
        .build()
    )
    
    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.admitted_from_concept is not None
    assert len(criteria.criteria.admitted_from_concept) == 1
    assert criteria.criteria.admitted_from_concept[0].concept_id == 8715


def test_observation_with_qualifier():
    """Test observation qualifier modifier."""
    cohort = (
        CohortBuilder("Test Observation Qualifier")
        .with_condition(1)
        .begin_rule("Observation Rule")
        .require_observation(10).with_qualifier(4214956).anytime_before()
        .build()
    )
    
    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.qualifier is not None
    assert len(criteria.criteria.qualifier) == 1
    assert criteria.criteria.qualifier[0].concept_id == 4214956


def test_multiple_modifiers_chained():
    """Test chaining multiple modifiers on one criterion."""
    cohort = (
        CohortBuilder("Test Multi-Modifier")
        .with_condition(1)
        .begin_rule("Drug Rule")
        .require_drug(10)\
            .with_route(4132161)\
            .with_refills(min_refills=2, max_refills=6)\
            .with_dose(min_dose=5.0, max_dose=20.0)\
            .with_days_supply(min_days=30, max_days=90)\
            .anytime_before()
        .build()
    )
    
    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.route_concept is not None
    assert criteria.criteria.refills is not None  
    assert criteria.criteria.effective_drug_dose is not None
    assert criteria.criteria.days_supply is not None
