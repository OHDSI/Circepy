"""
Unit tests for CohortComposer module.

Tests the fluent API for building cohort definitions.
"""

from circe.capr import (
    acute_disease_cohort,
    at_least,
    at_most,
    attrition,
    chronic_disease_cohort,
    cohort,
    condition_era,
    condition_occurrence,
    continuous_observation,
    death,
    device_exposure,
    dose_era,
    drug_era,
    drug_exposure,
    during_interval,
    entry,
    era,
    event_ends,
    event_starts,
    exactly,
    exit_strategy,
    location_region,
    measurement,
    new_user_drug_cohort,
    observation,
    observation_period,
    payer_plan_period,
    procedure,
    sensitive_disease_cohort,
    specific_disease_cohort,
    specimen,
    visit,
    visit_detail,
    with_all,
    with_any,
)
from circe.vocabulary import concept_set, descendants, exclude, mapped


class TestQueryFunctions:
    """Test domain query functions."""

    def test_condition_occurrence_basic(self):
        query = condition_occurrence(concept_set_id=1)
        assert query.domain == "ConditionOccurrence"
        assert query.concept_set_id == 1
        assert query.first_occurrence is False

    def test_condition_occurrence_first(self):
        query = condition_occurrence(concept_set_id=1, first_occurrence=True)
        assert query.first_occurrence is True

    def test_condition_occurrence_with_age(self):
        query = condition_occurrence(concept_set_id=1, age=(18, 65))
        assert query.criteria_options["age"] == (18, 65)

    def test_drug_exposure_basic(self):
        query = drug_exposure(concept_set_id=2)
        assert query.domain == "DrugExposure"
        assert query.concept_set_id == 2

    def test_drug_exposure_with_days_supply(self):
        query = drug_exposure(concept_set_id=2, days_supply=(30, 90))
        assert query.criteria_options["days_supply"] == (30, 90)

    def test_drug_era(self):
        query = drug_era(concept_set_id=2, first_occurrence=True)
        assert query.domain == "DrugEra"
        assert query.first_occurrence is True

    def test_measurement(self):
        query = measurement(concept_set_id=3, value_as_number=(6.5, 10.0))
        assert query.domain == "Measurement"
        assert query.criteria_options["value_as_number"] == (6.5, 10.0)

    def test_procedure(self):
        query = procedure(concept_set_id=4)
        assert query.domain == "ProcedureOccurrence"

    def test_all_domains_create_valid_queries(self):
        """Test that all domain query functions work."""
        queries = [
            condition_occurrence(concept_set_id=1),
            condition_era(concept_set_id=1),
            drug_exposure(concept_set_id=1),
            drug_era(concept_set_id=1),
            dose_era(concept_set_id=1),
            procedure(concept_set_id=1),
            measurement(concept_set_id=1),
            observation(concept_set_id=1),
            visit(concept_set_id=1),
            visit_detail(concept_set_id=1),
            device_exposure(concept_set_id=1),
            specimen(concept_set_id=1),
            death(),
            observation_period(),
            payer_plan_period(concept_set_id=1),
            location_region(concept_set_id=1),
        ]
        assert len(queries) == 16


class TestWindowFunctions:
    """Test time window functions."""

    def test_event_starts(self):
        interval = event_starts(before=365, after=0)
        assert interval.start == 365
        assert interval.end == 0
        assert interval.index == "startDate"

    def test_event_ends(self):
        interval = event_ends(before=0, after=30)
        assert interval.start == 0
        assert interval.end == 30
        assert interval.index == "endDate"

    def test_during_interval(self):
        window = during_interval(start_window=event_starts(before=365, after=0))
        assert window.start_window is not None
        assert window.start_window.start == 365

    def test_continuous_observation(self):
        obs = continuous_observation(prior_days=365, post_days=0)
        assert obs.prior_days == 365
        assert obs.post_days == 0


class TestCriteriaFunctions:
    """Test occurrence counting functions."""

    def test_at_least(self):
        criteria = at_least(
            count=2,
            query=drug_exposure(concept_set_id=1),
            aperture=during_interval(event_starts(before=365, after=0)),
        )
        assert criteria.occurrence_type == "atLeast"
        assert criteria.count == 2

    def test_at_most(self):
        criteria = at_most(
            count=1,
            query=condition_occurrence(concept_set_id=1),
            aperture=during_interval(event_starts(before=365, after=0)),
        )
        assert criteria.occurrence_type == "atMost"
        assert criteria.count == 1

    def test_exactly(self):
        criteria = exactly(
            count=0,
            query=drug_exposure(concept_set_id=1),
            aperture=during_interval(event_starts(before=365, after=1)),
        )
        assert criteria.occurrence_type == "exactly"
        assert criteria.count == 0

    def test_with_all(self):
        group = with_all(at_least(1, condition_occurrence(1)), at_least(1, drug_exposure(2)))
        assert group.group_type == "ALL"
        assert len(group.criteria_list) == 2

    def test_with_any(self):
        group = with_any(at_least(1, condition_occurrence(1)), at_least(1, condition_occurrence(2)))
        assert group.group_type == "ANY"
        assert len(group.criteria_list) == 2


class TestAttrition:
    """Test attrition functions."""

    def test_attrition_single_rule(self):
        rules = attrition(no_prior_drug=with_all(exactly(0, drug_exposure(1))))
        assert len(rules.rules) == 1
        assert rules.rules[0].name == "no prior drug"

    def test_attrition_multiple_rules(self):
        rules = attrition(
            rule_one=with_all(at_least(1, condition_occurrence(1))),
            rule_two=with_all(exactly(0, drug_exposure(2))),
        )
        assert len(rules.rules) == 2


class TestCohortConstruction:
    """Test main cohort construction functions."""

    def test_simple_entry_cohort(self):
        c = cohort(
            title="Simple Cohort",
            entry=entry(
                condition_occurrence(concept_set_id=1, first_occurrence=True), observation_window=(365, 0)
            ),
        )
        assert c.title == "Simple Cohort"
        assert c.entry_event is not None
        assert c.entry_event.observation_window.prior_days == 365

    def test_cohort_with_attrition(self):
        c = cohort(
            title="Cohort with Attrition",
            entry=entry(
                condition_occurrence(concept_set_id=1, first_occurrence=True), observation_window=(365, 0)
            ),
            attrition=attrition(
                no_prior_drug=with_all(
                    exactly(0, drug_exposure(2), during_interval(event_starts(before=365, after=1)))
                )
            ),
        )
        assert c.attrition is not None
        assert len(c.attrition.rules) == 1

    def test_build_produces_cohort_expression(self):
        c = cohort(
            title="Build Test",
            entry=entry(
                condition_occurrence(concept_set_id=1, first_occurrence=True), observation_window=(365, 0)
            ),
        )
        expr = c.build()
        assert expr.title == "Build Test"
        assert expr.primary_criteria is not None

    def test_exit_strategy_observation(self):
        ex = exit_strategy(end_strategy="observation")
        assert ex.strategy_type == "observation"

    def test_exit_strategy_date_offset(self):
        ex = exit_strategy(end_strategy="date_offset", offset_days=365)
        assert ex.strategy_type == "date_offset"
        assert ex.offset_days == 365


class TestTemplates:
    """Test generic cohort templates."""

    def test_sensitive_disease_cohort(self):
        expr = sensitive_disease_cohort(concept_set_id=1, title="Sensitive Test")
        assert expr.title == "Sensitive Test"
        assert expr.primary_criteria is not None

    def test_specific_disease_cohort(self):
        expr = specific_disease_cohort(concept_set_id=1, confirmation_days=30, title="Specific Test")
        assert expr.title == "Specific Test"
        assert expr.inclusion_rules is not None

    def test_acute_disease_cohort(self):
        expr = acute_disease_cohort(concept_set_id=1, washout_days=180, title="Acute Test")
        assert expr.title == "Acute Test"
        assert expr.inclusion_rules is not None

    def test_chronic_disease_cohort(self):
        expr = chronic_disease_cohort(concept_set_id=1, lookback_days=365, title="Chronic Test")
        assert expr.title == "Chronic Test"
        assert expr.inclusion_rules is not None

    def test_new_user_drug_cohort(self):
        expr = new_user_drug_cohort(drug_concept_set_id=2, washout_days=365, title="New User Test")
        assert expr.title == "New User Test"
        assert expr.inclusion_rules is not None


class TestConceptSetHelpers:
    """Test vocabulary helper functions."""

    def test_descendants(self):
        ref = descendants(201826)
        assert ref.concept_id == 201826
        assert ref.include_descendants is True

    def test_mapped(self):
        ref = mapped(201826)
        assert ref.concept_id == 201826
        assert ref.include_mapped is True

    def test_exclude_int(self):
        ref = exclude(201826)
        assert ref.concept_id == 201826
        assert ref.is_excluded is True

    def test_exclude_reference(self):
        ref = exclude(descendants(201826))
        assert ref.concept_id == 201826
        assert ref.include_descendants is True
        assert ref.is_excluded is True

    def test_concept_set_simple(self):
        cs = concept_set(201826, name="T2DM")
        assert cs.name == "T2DM"
        assert len(cs.expression.items) == 1

    def test_concept_set_with_descendants(self):
        cs = concept_set(descendants(201826), name="T2DM with descendants")
        assert cs.expression.items[0].include_descendants is True

    def test_concept_set_multiple(self):
        cs = concept_set(descendants(201826), descendants(201254), name="Multiple Diabetes")
        assert len(cs.expression.items) == 2


class TestIntegration:
    """Integration tests for full cohort building."""

    def test_full_cohort_with_all_components(self):
        c = cohort(
            title="Full Integration Test",
            entry=entry(
                drug_exposure(concept_set_id=2, first_occurrence=True),
                observation_window=(365, 0),
                primary_criteria_limit="First",
            ),
            attrition=attrition(
                has_indication=with_all(
                    at_least(1, condition_occurrence(1), during_interval(event_starts(before=365, after=0)))
                ),
                no_prior_drug=with_all(
                    exactly(0, drug_exposure(2), during_interval(event_starts(before=365, after=1)))
                ),
            ),
            exit=exit_strategy(end_strategy="observation"),
            era=era(era_days=0),
        )

        expr = c.build()
        assert expr.title == "Full Integration Test"
        assert expr.primary_criteria is not None
        assert expr.inclusion_rules is not None
        assert len(expr.inclusion_rules) == 2
