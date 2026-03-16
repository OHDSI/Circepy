"""
Tests for circe.helper.cohort_modifiers

Covers all 12 modifier functions, reset helpers, chaining, and apply_standard_rules.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from circe.cohortdefinition import (
    CohortExpression,
    Death,
    DrugExposure,
)
from circe.cohortdefinition.core import (
    CollapseType,
    CustomEraStrategy,
    DateOffsetStrategy,
)
from circe.helper.cohort_modifiers import (
    GENDER_FEMALE_CONCEPT_ID,
    # Constants
    GENDER_MALE_CONCEPT_ID,
    # Convenience
    apply_standard_rules,
    clear_censor_events,
    reset_age_criteria,
    reset_clean_window,
    reset_collapse_settings,
    reset_date_range,
    reset_end_strategy,
    reset_gender_criteria,
    # Resets
    reset_observation_window,
    set_age_criteria,
    set_allow_all_events,
    set_censor_event,
    set_clean_window,
    set_cohort_era,
    set_date_range,
    set_end_date_strategy,
    set_gender_criteria,
    set_limit_to_first_event,
    set_post_observation,
    # Modifiers
    set_prior_observation,
    set_washout_period,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXAMPLE_JSON = (
    Path(__file__).resolve().parent.parent / "examples" / "type2_diabetes_cohort.json"
)


@pytest.fixture
def empty_cohort() -> CohortExpression:
    """Minimal empty cohort expression."""
    return CohortExpression()


@pytest.fixture
def diabetes_cohort() -> CohortExpression:
    """Cohort loaded from the example type-2 diabetes JSON."""
    with open(EXAMPLE_JSON) as f:
        data = json.load(f)
    return CohortExpression.model_validate(data)


# ===========================================================================
# 1. Prior Observation
# ===========================================================================


class TestSetPriorObservation:
    def test_sets_prior_days(self, empty_cohort):
        result = set_prior_observation(empty_cohort, 365)
        assert result is empty_cohort  # same object (chaining)
        assert result.primary_criteria.observation_window.prior_days == 365

    def test_updates_existing(self, diabetes_cohort):
        set_prior_observation(diabetes_cohort, 180)
        assert diabetes_cohort.primary_criteria.observation_window.prior_days == 180

    def test_zero_days(self, empty_cohort):
        set_prior_observation(empty_cohort, 0)
        assert empty_cohort.primary_criteria.observation_window.prior_days == 0

    def test_negative_raises(self, empty_cohort):
        with pytest.raises(ValueError, match="days must be >= 0"):
            set_prior_observation(empty_cohort, -1)


# ===========================================================================
# 2. Post Observation
# ===========================================================================


class TestSetPostObservation:
    def test_sets_post_days(self, empty_cohort):
        result = set_post_observation(empty_cohort, 30)
        assert result is empty_cohort
        assert result.primary_criteria.observation_window.post_days == 30

    def test_updates_existing(self, diabetes_cohort):
        set_post_observation(diabetes_cohort, 60)
        assert diabetes_cohort.primary_criteria.observation_window.post_days == 60

    def test_negative_raises(self, empty_cohort):
        with pytest.raises(ValueError):
            set_post_observation(empty_cohort, -10)


# ===========================================================================
# 3. Limit to First Event
# ===========================================================================


class TestSetLimitToFirstEvent:
    def test_sets_first(self, empty_cohort):
        result = set_limit_to_first_event(empty_cohort)
        assert result is empty_cohort
        assert result.primary_criteria.primary_limit.type == "First"
        assert result.expression_limit.type == "First"

    def test_overrides_all(self, diabetes_cohort):
        # Diabetes cohort starts with "All"
        set_limit_to_first_event(diabetes_cohort)
        assert diabetes_cohort.primary_criteria.primary_limit.type == "First"
        assert diabetes_cohort.expression_limit.type == "First"


# ===========================================================================
# 4. Allow All Events
# ===========================================================================


class TestSetAllowAllEvents:
    def test_sets_all(self, empty_cohort):
        set_limit_to_first_event(empty_cohort)  # first set to first
        result = set_allow_all_events(empty_cohort)
        assert result is empty_cohort
        assert result.primary_criteria.primary_limit.type == "All"
        assert result.expression_limit.type == "All"


# ===========================================================================
# 6. Cohort Era
# ===========================================================================


class TestSetCohortEra:
    def test_sets_era_pad(self, empty_cohort):
        result = set_cohort_era(empty_cohort, 30)
        assert result is empty_cohort
        assert result.collapse_settings.era_pad == 30
        assert result.collapse_settings.collapse_type == CollapseType.ERA

    def test_zero_gap(self, empty_cohort):
        set_cohort_era(empty_cohort, 0)
        assert empty_cohort.collapse_settings.era_pad == 0

    def test_negative_raises(self, empty_cohort):
        with pytest.raises(ValueError, match="era_gap_days must be >= 0"):
            set_cohort_era(empty_cohort, -5)


# ===========================================================================
# 7. Age Criteria
# ===========================================================================


class TestSetAgeCriteria:
    def test_both_bounds(self, empty_cohort):
        result = set_age_criteria(empty_cohort, min_age=18, max_age=65)
        assert result is empty_cohort
        dc = result.additional_criteria.demographic_criteria_list[0]
        assert dc.age.op == "bt"
        assert dc.age.value == 18
        assert dc.age.extent == 65

    def test_min_only(self, empty_cohort):
        set_age_criteria(empty_cohort, min_age=18)
        dc = empty_cohort.additional_criteria.demographic_criteria_list[0]
        assert dc.age.op == "gte"
        assert dc.age.value == 18

    def test_max_only(self, empty_cohort):
        set_age_criteria(empty_cohort, max_age=100)
        dc = empty_cohort.additional_criteria.demographic_criteria_list[0]
        assert dc.age.op == "lte"
        assert dc.age.value == 100

    def test_no_bounds_raises(self, empty_cohort):
        with pytest.raises(ValueError, match="At least one"):
            set_age_criteria(empty_cohort)

    def test_inverted_bounds_raises(self, empty_cohort):
        with pytest.raises(ValueError, match="min_age.*must be <= max_age"):
            set_age_criteria(empty_cohort, min_age=65, max_age=18)

    def test_appends_to_existing(self, empty_cohort):
        set_age_criteria(empty_cohort, min_age=18)
        set_age_criteria(empty_cohort, max_age=100)
        assert len(empty_cohort.additional_criteria.demographic_criteria_list) == 2


# ===========================================================================
# 8. Gender Criteria
# ===========================================================================


class TestSetGenderCriteria:
    def test_female(self, empty_cohort):
        result = set_gender_criteria(empty_cohort, GENDER_FEMALE_CONCEPT_ID)
        assert result is empty_cohort
        dc = result.additional_criteria.demographic_criteria_list[0]
        assert len(dc.gender) == 1
        assert dc.gender[0].concept_id == GENDER_FEMALE_CONCEPT_ID

    def test_male(self, empty_cohort):
        set_gender_criteria(empty_cohort, GENDER_MALE_CONCEPT_ID)
        dc = empty_cohort.additional_criteria.demographic_criteria_list[0]
        assert dc.gender[0].concept_id == GENDER_MALE_CONCEPT_ID
        assert dc.gender[0].concept_name == "MALE"

    def test_multiple_genders(self, empty_cohort):
        set_gender_criteria(
            empty_cohort, [GENDER_MALE_CONCEPT_ID, GENDER_FEMALE_CONCEPT_ID]
        )
        dc = empty_cohort.additional_criteria.demographic_criteria_list[0]
        assert len(dc.gender) == 2

    def test_unknown_concept_id(self, empty_cohort):
        set_gender_criteria(empty_cohort, 99999)
        dc = empty_cohort.additional_criteria.demographic_criteria_list[0]
        assert dc.gender[0].concept_id == 99999

    def test_appends_to_existing_criteria(self, empty_cohort):
        set_age_criteria(empty_cohort, min_age=18)
        set_gender_criteria(empty_cohort, GENDER_FEMALE_CONCEPT_ID)
        assert len(empty_cohort.additional_criteria.demographic_criteria_list) == 2


# ===========================================================================
# 9. End Date Strategy
# ===========================================================================


class TestSetEndDateStrategy:
    def test_fixed_duration(self, empty_cohort):
        result = set_end_date_strategy(empty_cohort, "fixed_duration", days=180)
        assert result is empty_cohort
        assert isinstance(result.end_strategy, DateOffsetStrategy)
        assert result.end_strategy.offset == 180
        assert result.end_strategy.date_field == "StartDate"

    def test_fixed_duration_end_date(self, empty_cohort):
        set_end_date_strategy(
            empty_cohort, "fixed_duration", days=90, date_field="EndDate"
        )
        assert empty_cohort.end_strategy.date_field == "EndDate"

    def test_fixed_duration_no_days_raises(self, empty_cohort):
        with pytest.raises(ValueError, match="days is required"):
            set_end_date_strategy(empty_cohort, "fixed_duration")

    def test_end_of_observation(self, empty_cohort):
        # First set a strategy, then clear it
        set_end_date_strategy(empty_cohort, "fixed_duration", days=30)
        set_end_date_strategy(empty_cohort, "end_of_observation")
        assert empty_cohort.end_strategy is None

    def test_custom_era(self, empty_cohort):
        set_end_date_strategy(
            empty_cohort,
            "custom_era",
            drug_codeset_id=1,
            gap_days=30,
            offset=7,
        )
        assert isinstance(empty_cohort.end_strategy, CustomEraStrategy)
        assert empty_cohort.end_strategy.drug_codeset_id == 1
        assert empty_cohort.end_strategy.gap_days == 30
        assert empty_cohort.end_strategy.offset == 7

    def test_unknown_strategy_raises(self, empty_cohort):
        with pytest.raises(ValueError, match="Unknown strategy"):
            set_end_date_strategy(empty_cohort, "unknown_strategy")

    def test_strategy_name_normalization(self, empty_cohort):
        set_end_date_strategy(empty_cohort, "Fixed-Duration", days=10)
        assert isinstance(empty_cohort.end_strategy, DateOffsetStrategy)

        set_end_date_strategy(empty_cohort, "observation_period")
        assert empty_cohort.end_strategy is None


# ===========================================================================
# 10. Washout Period
# ===========================================================================


class TestSetWashoutPeriod:
    def test_sets_prior_observation_only(self, empty_cohort):
        """Washout sets prior observation but does NOT force first event."""
        result = set_washout_period(empty_cohort, 365)
        assert result is empty_cohort
        assert result.primary_criteria.observation_window.prior_days == 365
        # Washout should NOT touch the event limit
        assert result.expression_limit is None

    def test_preserves_all_events_limit(self, empty_cohort):
        """Washout should not change an existing 'All' event limit."""
        set_allow_all_events(empty_cohort)
        set_washout_period(empty_cohort, 180)
        assert empty_cohort.primary_criteria.primary_limit.type == "All"
        assert empty_cohort.primary_criteria.observation_window.prior_days == 180

    def test_zero_days(self, empty_cohort):
        set_washout_period(empty_cohort, 0)
        assert empty_cohort.primary_criteria.observation_window.prior_days == 0

    def test_negative_raises(self, empty_cohort):
        with pytest.raises(ValueError):
            set_washout_period(empty_cohort, -1)


# ===========================================================================
# 10b. Clean Window
# ===========================================================================


class TestSetCleanWindow:
    def test_adds_inclusion_rule(self, diabetes_cohort):
        """A clean window adds an inclusion rule to deduplicate events."""
        result = set_clean_window(diabetes_cohort, 7)
        assert result is diabetes_cohort
        # Should have added exactly one inclusion rule
        matching = [
            r
            for r in result.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        ]
        assert len(matching) == 1

    def test_single_criterion_defaults_to_any_mode(self, diabetes_cohort):
        """With one primary criterion and default mode, group type is ALL."""
        assert len(diabetes_cohort.primary_criteria.criteria_list) == 1
        set_clean_window(diabetes_cohort, 30)
        rule = next(
            r
            for r in diabetes_cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        assert rule.description is not None
        assert "30" in rule.description
        assert "criteria_mode=any" in rule.description
        group = rule.expression
        assert group is not None
        assert group.type == "ALL"
        assert len(group.criteria_list) == 1
        correlated = group.criteria_list[0]
        assert correlated.occurrence.type == 0  # EXACTLY
        assert correlated.occurrence.count == 0
        assert correlated.start_window.start.coeff == -1
        assert correlated.start_window.start.days == 30
        assert correlated.start_window.end.coeff == -1
        assert correlated.start_window.end.days == 1

    def test_single_criterion_both_modes_equivalent(self, diabetes_cohort):
        """With one criterion, 'any' and 'all' produce the same correlated list."""
        set_clean_window(diabetes_cohort, 7, criteria_mode="any")
        rule_any = next(
            r
            for r in diabetes_cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        n_any = len(rule_any.expression.criteria_list)

        set_clean_window(diabetes_cohort, 7, criteria_mode="all")
        rule_all = next(
            r
            for r in diabetes_cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        n_all = len(rule_all.expression.criteria_list)

        # Same count (1), but different group types
        assert n_any == n_all == 1
        assert rule_any.expression.type == "ALL"
        assert rule_all.expression.type == "ANY"

    # -----------------------------------------------------------------------
    # criteria_mode="any" (default) – OR-style primary criteria
    # -----------------------------------------------------------------------

    def test_any_mode_multi_criteria_uses_all_group(self):
        """mode='any': group type is ALL so every criterion must show 0 prior."""
        cohort = CohortExpression.model_validate(
            {
                "PrimaryCriteria": {
                    "CriteriaList": [
                        {"ConditionOccurrence": {"CodesetId": 1, "First": True}},
                        {"DrugExposure": {"CodesetId": 2, "First": True}},
                    ],
                    "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
                    "PrimaryCriteriaLimit": {"Type": "All"},
                }
            }
        )
        set_clean_window(cohort, 7, criteria_mode="any")
        rule = next(
            r
            for r in cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        group = rule.expression
        assert group.type == "ALL"
        assert len(group.criteria_list) == 2

        criteria_types = set()
        for correlated in group.criteria_list:
            criteria_types.add(type(correlated.criteria).__name__)
            assert correlated.occurrence.type == 0
            assert correlated.occurrence.count == 0
            assert correlated.start_window.start.days == 7
        assert criteria_types == {"ConditionOccurrence", "DrugExposure"}

    # -----------------------------------------------------------------------
    # criteria_mode="all" – AND-style primary criteria
    # -----------------------------------------------------------------------

    def test_all_mode_multi_criteria_uses_any_group(self):
        """mode='all': group type is ANY – event passes if any criterion was absent."""
        cohort = CohortExpression.model_validate(
            {
                "PrimaryCriteria": {
                    "CriteriaList": [
                        {"ConditionOccurrence": {"CodesetId": 1, "First": True}},
                        {"DrugExposure": {"CodesetId": 2, "First": True}},
                    ],
                    "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
                    "PrimaryCriteriaLimit": {"Type": "All"},
                }
            }
        )
        set_clean_window(cohort, 7, criteria_mode="all")
        rule = next(
            r
            for r in cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        group = rule.expression
        assert group.type == "ANY"
        assert len(group.criteria_list) == 2
        assert "criteria_mode=all" in rule.description

    def test_all_mode_three_criteria(self):
        """mode='all' scales to three criteria with ANY group."""
        cohort = CohortExpression.model_validate(
            {
                "PrimaryCriteria": {
                    "CriteriaList": [
                        {"ConditionOccurrence": {"CodesetId": 1, "First": True}},
                        {"DrugExposure": {"CodesetId": 2, "First": True}},
                        {"ProcedureOccurrence": {"CodesetId": 3, "First": True}},
                    ],
                    "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
                    "PrimaryCriteriaLimit": {"Type": "All"},
                }
            }
        )
        set_clean_window(cohort, 14, criteria_mode="all")
        rule = next(
            r
            for r in cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        assert rule.expression.type == "ANY"
        assert len(rule.expression.criteria_list) == 3

    # -----------------------------------------------------------------------
    # Invalid criteria_mode
    # -----------------------------------------------------------------------

    def test_invalid_criteria_mode_raises(self, diabetes_cohort):
        with pytest.raises(ValueError, match="criteria_mode must be"):
            set_clean_window(diabetes_cohort, 7, criteria_mode="first")

    # -----------------------------------------------------------------------
    # Replace, reset, edge cases
    # -----------------------------------------------------------------------

    def test_replaces_existing_clean_window(self, diabetes_cohort):
        """Calling set_clean_window twice replaces the old rule."""
        set_clean_window(diabetes_cohort, 7)
        set_clean_window(diabetes_cohort, 14)
        matching = [
            r
            for r in diabetes_cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        ]
        assert len(matching) == 1
        assert "14" in matching[0].description

    def test_replace_changes_mode(self, diabetes_cohort):
        """Replacing a clean window can switch from 'any' to 'all'."""
        set_clean_window(diabetes_cohort, 7, criteria_mode="any")
        rule = next(
            r
            for r in diabetes_cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        assert rule.expression.type == "ALL"

        set_clean_window(diabetes_cohort, 7, criteria_mode="all")
        rule = next(
            r
            for r in diabetes_cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        assert rule.expression.type == "ANY"

    def test_preserves_other_inclusion_rules(self, diabetes_cohort):
        """Clean window should not remove user-defined inclusion rules."""
        from circe.cohortdefinition.criteria import InclusionRule as IR

        user_rule = IR(name="my_rule", description="custom")
        diabetes_cohort.inclusion_rules.append(user_rule)
        set_clean_window(diabetes_cohort, 7)
        names = [getattr(r, "name", None) for r in diabetes_cohort.inclusion_rules]
        assert "my_rule" in names
        assert "__clean_window__" in names

    def test_no_primary_criteria_raises(self, empty_cohort):
        """Cannot set a clean window if no primary criteria exist."""
        with pytest.raises(ValueError, match="primary criteria"):
            set_clean_window(empty_cohort, 7)

    def test_days_less_than_1_raises(self, diabetes_cohort):
        with pytest.raises(ValueError, match="days must be >= 1"):
            set_clean_window(diabetes_cohort, 0)

    def test_negative_days_raises(self, diabetes_cohort):
        with pytest.raises(ValueError):
            set_clean_window(diabetes_cohort, -5)

    def test_reset_clean_window(self, diabetes_cohort):
        """reset_clean_window removes only the clean-window rule."""
        from circe.cohortdefinition.criteria import InclusionRule as IR

        user_rule = IR(name="keep_me", description="custom")
        diabetes_cohort.inclusion_rules.append(user_rule)
        set_clean_window(diabetes_cohort, 7)
        assert len(diabetes_cohort.inclusion_rules) == 2
        reset_clean_window(diabetes_cohort)
        assert len(diabetes_cohort.inclusion_rules) == 1
        assert diabetes_cohort.inclusion_rules[0].name == "keep_me"

    def test_reset_clean_window_noop_when_absent(self, empty_cohort):
        """reset_clean_window should not raise when no rule is present."""
        result = reset_clean_window(empty_cohort)
        assert result is empty_cohort

    def test_replace_updates_count_after_criteria_change(self):
        """If primary criteria change between calls, the new rule reflects them."""
        from circe.cohortdefinition import DrugExposure

        cohort = CohortExpression.model_validate(
            {
                "PrimaryCriteria": {
                    "CriteriaList": [
                        {"ConditionOccurrence": {"CodesetId": 1, "First": True}},
                    ],
                    "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
                    "PrimaryCriteriaLimit": {"Type": "All"},
                }
            }
        )
        set_clean_window(cohort, 7)
        rule = next(
            r
            for r in cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        assert len(rule.expression.criteria_list) == 1

        # Now add a second primary criterion and reset the clean window
        cohort.primary_criteria.criteria_list.append(DrugExposure(codeset_id=2))
        set_clean_window(cohort, 7)
        rule = next(
            r
            for r in cohort.inclusion_rules
            if getattr(r, "name", None) == "__clean_window__"
        )
        assert len(rule.expression.criteria_list) == 2


# ===========================================================================
# 11. Date Range
# ===========================================================================


class TestSetDateRange:
    def test_both_dates_string(self, empty_cohort):
        result = set_date_range(
            empty_cohort, start_date="2020-01-01", end_date="2022-12-31"
        )
        assert result is empty_cohort
        assert result.censor_window.start_date == "2020-01-01"
        assert result.censor_window.end_date == "2022-12-31"

    def test_date_objects(self, empty_cohort):
        set_date_range(
            empty_cohort, start_date=date(2020, 1, 1), end_date=date(2022, 12, 31)
        )
        assert empty_cohort.censor_window.start_date == "2020-01-01"
        assert empty_cohort.censor_window.end_date == "2022-12-31"

    def test_start_only(self, empty_cohort):
        set_date_range(empty_cohort, start_date="2020-01-01")
        assert empty_cohort.censor_window.start_date == "2020-01-01"
        assert empty_cohort.censor_window.end_date is None

    def test_end_only(self, empty_cohort):
        set_date_range(empty_cohort, end_date="2022-12-31")
        assert empty_cohort.censor_window.start_date is None
        assert empty_cohort.censor_window.end_date == "2022-12-31"

    def test_no_dates_raises(self, empty_cohort):
        with pytest.raises(ValueError, match="At least one"):
            set_date_range(empty_cohort)


# ===========================================================================
# 12. Censor at Event
# ===========================================================================


class TestSetCensorEvent:
    def test_add_death(self, empty_cohort):
        death = Death()
        result = set_censor_event(empty_cohort, death)
        assert result is empty_cohort
        assert len(result.censoring_criteria) == 1
        assert isinstance(result.censoring_criteria[0], Death)

    def test_add_multiple(self, empty_cohort):
        set_censor_event(empty_cohort, Death())
        set_censor_event(empty_cohort, DrugExposure(codeset_id=1))
        assert len(empty_cohort.censoring_criteria) == 2

    def test_clear(self, empty_cohort):
        set_censor_event(empty_cohort, Death())
        set_censor_event(empty_cohort, Death())
        clear_censor_events(empty_cohort)
        assert len(empty_cohort.censoring_criteria) == 0


# ===========================================================================
# Reset helpers
# ===========================================================================


class TestResetFunctions:
    def test_reset_observation_window(self, empty_cohort):
        set_prior_observation(empty_cohort, 365)
        reset_observation_window(empty_cohort)
        assert empty_cohort.primary_criteria.observation_window is None

    def test_reset_observation_window_no_pc(self, empty_cohort):
        # Should not raise on an empty cohort
        result = reset_observation_window(empty_cohort)
        assert result is empty_cohort

    def test_reset_age_criteria(self, empty_cohort):
        set_age_criteria(empty_cohort, min_age=18)
        reset_age_criteria(empty_cohort)
        assert len(empty_cohort.additional_criteria.demographic_criteria_list) == 0

    def test_reset_age_preserves_gender(self, empty_cohort):
        set_age_criteria(empty_cohort, min_age=18)
        set_gender_criteria(empty_cohort, GENDER_FEMALE_CONCEPT_ID)
        reset_age_criteria(empty_cohort)
        assert len(empty_cohort.additional_criteria.demographic_criteria_list) == 1
        assert (
            empty_cohort.additional_criteria.demographic_criteria_list[0].gender
            is not None
        )

    def test_reset_gender_criteria(self, empty_cohort):
        set_gender_criteria(empty_cohort, GENDER_MALE_CONCEPT_ID)
        reset_gender_criteria(empty_cohort)
        assert len(empty_cohort.additional_criteria.demographic_criteria_list) == 0

    def test_reset_gender_preserves_age(self, empty_cohort):
        set_age_criteria(empty_cohort, min_age=18)
        set_gender_criteria(empty_cohort, GENDER_MALE_CONCEPT_ID)
        reset_gender_criteria(empty_cohort)
        assert len(empty_cohort.additional_criteria.demographic_criteria_list) == 1
        assert (
            empty_cohort.additional_criteria.demographic_criteria_list[0].age
            is not None
        )

    def test_reset_end_strategy(self, empty_cohort):
        set_end_date_strategy(empty_cohort, "fixed_duration", days=30)
        reset_end_strategy(empty_cohort)
        assert empty_cohort.end_strategy is None

    def test_reset_collapse_settings(self, empty_cohort):
        set_cohort_era(empty_cohort, 30)
        reset_collapse_settings(empty_cohort)
        assert empty_cohort.collapse_settings is None

    def test_reset_date_range(self, empty_cohort):
        set_date_range(empty_cohort, start_date="2020-01-01")
        reset_date_range(empty_cohort)
        assert empty_cohort.censor_window is None


# ===========================================================================
# Chaining
# ===========================================================================


class TestChaining:
    def test_chain_multiple_modifiers(self, empty_cohort):
        result = set_prior_observation(
            set_post_observation(
                set_limit_to_first_event(set_cohort_era(empty_cohort, 0)), 30
            ),
            365,
        )
        assert result is empty_cohort
        assert result.primary_criteria.observation_window.prior_days == 365
        assert result.primary_criteria.observation_window.post_days == 30
        assert result.primary_criteria.primary_limit.type == "First"
        assert result.collapse_settings.era_pad == 0


# ===========================================================================
# apply_standard_rules
# ===========================================================================


class TestApplyStandardRules:
    def test_defaults(self, empty_cohort):
        result = apply_standard_rules(empty_cohort)
        assert result is empty_cohort
        assert result.primary_criteria.observation_window.prior_days == 365
        assert result.primary_criteria.observation_window.post_days == 0
        assert result.primary_criteria.primary_limit.type == "First"
        assert result.expression_limit.type == "First"
        assert result.collapse_settings.era_pad == 0

    def test_custom_values(self, empty_cohort):
        apply_standard_rules(
            empty_cohort,
            prior_observation_days=180,
            post_observation_days=30,
            first_event_only=False,
            era_gap_days=14,
            min_age=18,
            max_age=65,
            gender_concept_ids=GENDER_FEMALE_CONCEPT_ID,
            end_strategy="fixed_duration",
            end_strategy_days=365,
        )
        assert empty_cohort.primary_criteria.observation_window.prior_days == 180
        assert empty_cohort.primary_criteria.observation_window.post_days == 30
        assert empty_cohort.primary_criteria.primary_limit.type == "All"
        assert empty_cohort.collapse_settings.era_pad == 14
        dc_list = empty_cohort.additional_criteria.demographic_criteria_list
        # One for age, one for gender
        assert len(dc_list) == 2
        assert isinstance(empty_cohort.end_strategy, DateOffsetStrategy)
        assert empty_cohort.end_strategy.offset == 365

    def test_no_optional_params(self, empty_cohort):
        apply_standard_rules(empty_cohort, prior_observation_days=0)
        assert empty_cohort.primary_criteria.observation_window.prior_days == 0
        assert empty_cohort.additional_criteria is None

    def test_on_real_cohort(self, diabetes_cohort):
        apply_standard_rules(
            diabetes_cohort,
            prior_observation_days=365,
            first_event_only=True,
            min_age=40,
        )
        assert diabetes_cohort.primary_criteria.observation_window.prior_days == 365
        assert diabetes_cohort.primary_criteria.primary_limit.type == "First"
        assert diabetes_cohort.additional_criteria is not None
        dc = diabetes_cohort.additional_criteria.demographic_criteria_list[0]
        assert dc.age.op == "gte"
        assert dc.age.value == 40


# ===========================================================================
# JSON round-trip
# ===========================================================================


class TestJsonRoundTrip:
    def test_modified_cohort_serializes(self, diabetes_cohort):
        """Ensure a fully modified cohort can be serialized back to JSON."""
        set_prior_observation(diabetes_cohort, 180)
        set_limit_to_first_event(diabetes_cohort)
        set_cohort_era(diabetes_cohort, 30)
        set_age_criteria(diabetes_cohort, min_age=18, max_age=65)
        set_gender_criteria(diabetes_cohort, GENDER_FEMALE_CONCEPT_ID)
        set_end_date_strategy(diabetes_cohort, "fixed_duration", days=365)
        set_date_range(diabetes_cohort, start_date="2020-01-01", end_date="2023-12-31")
        set_censor_event(diabetes_cohort, Death())

        json_str = diabetes_cohort.model_dump_json()
        data = json.loads(json_str)

        # Verify key fields survived round-trip
        assert data["PrimaryCriteria"]["ObservationWindow"]["PriorDays"] == 180
        assert data["PrimaryCriteria"]["PrimaryCriteriaLimit"]["Type"] == "First"
        assert data["ExpressionLimit"]["Type"] == "First"
        assert data["CollapseSettings"]["EraPad"] == 30

    def test_modified_cohort_deserializes(self, diabetes_cohort):
        """Ensure a modified cohort can be serialized and parsed back."""
        set_prior_observation(diabetes_cohort, 180)
        set_limit_to_first_event(diabetes_cohort)
        set_cohort_era(diabetes_cohort, 30)

        json_str = diabetes_cohort.model_dump_json()
        parsed = CohortExpression.model_validate_json(json_str)

        assert parsed.primary_criteria.observation_window.prior_days == 180
        assert parsed.primary_criteria.primary_limit.type == "First"
        assert parsed.collapse_settings.era_pad == 30
