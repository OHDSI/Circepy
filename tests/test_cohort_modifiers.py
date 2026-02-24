"""
Tests for circe.helper.cohort_modifiers

Covers all 12 modifier functions, reset helpers, chaining, and apply_standard_rules.
"""

import json
import pytest
from datetime import date
from pathlib import Path

from circe.cohortdefinition import (
    CohortExpression,
    Death,
    DrugExposure,
)
from circe.cohortdefinition.core import (
    CollapseType,
    DateOffsetStrategy,
    CustomEraStrategy,
)
from circe.helper.cohort_modifiers import (
    # Constants
    GENDER_MALE_CONCEPT_ID,
    GENDER_FEMALE_CONCEPT_ID,
    # Modifiers
    set_prior_observation,
    set_post_observation,
    set_limit_to_first_event,
    set_allow_all_events,
    set_limit_to_n_events,
    set_cohort_era,
    set_age_criteria,
    set_gender_criteria,
    set_end_date_strategy,
    set_washout_period,
    set_date_range,
    set_censor_event,
    clear_censor_events,
    # Resets
    reset_observation_window,
    reset_age_criteria,
    reset_gender_criteria,
    reset_end_strategy,
    reset_collapse_settings,
    reset_date_range,
    # Convenience
    apply_standard_rules,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXAMPLE_JSON = Path(__file__).resolve().parent.parent / "examples" / "type2_diabetes_cohort.json"


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
# 5. Limit to N Events
# ===========================================================================

class TestSetLimitToNEvents:
    def test_n_equals_1(self, empty_cohort):
        result = set_limit_to_n_events(empty_cohort, 1)
        assert result.primary_criteria.primary_limit.type == "First"
        assert result.expression_limit.type == "First"

    def test_n_greater_than_1(self, empty_cohort):
        result = set_limit_to_n_events(empty_cohort, 5)
        assert result.primary_criteria.primary_limit.type == "All"
        assert result.expression_limit.type == "All"

    def test_n_zero_raises(self, empty_cohort):
        with pytest.raises(ValueError, match="n must be >= 1"):
            set_limit_to_n_events(empty_cohort, 0)

    def test_n_negative_raises(self, empty_cohort):
        with pytest.raises(ValueError):
            set_limit_to_n_events(empty_cohort, -1)


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
        set_gender_criteria(empty_cohort, [GENDER_MALE_CONCEPT_ID, GENDER_FEMALE_CONCEPT_ID])
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
        set_end_date_strategy(empty_cohort, "fixed_duration", days=90, date_field="EndDate")
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
            empty_cohort, "custom_era",
            drug_codeset_id=1, gap_days=30, offset=7,
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
    def test_sets_prior_and_first(self, empty_cohort):
        result = set_washout_period(empty_cohort, 365)
        assert result is empty_cohort
        assert result.primary_criteria.observation_window.prior_days == 365
        assert result.primary_criteria.primary_limit.type == "First"
        assert result.expression_limit.type == "First"

    def test_negative_raises(self, empty_cohort):
        with pytest.raises(ValueError):
            set_washout_period(empty_cohort, -1)


# ===========================================================================
# 11. Date Range
# ===========================================================================

class TestSetDateRange:
    def test_both_dates_string(self, empty_cohort):
        result = set_date_range(empty_cohort, start_date="2020-01-01", end_date="2022-12-31")
        assert result is empty_cohort
        assert result.censor_window.start_date == "2020-01-01"
        assert result.censor_window.end_date == "2022-12-31"

    def test_date_objects(self, empty_cohort):
        set_date_range(empty_cohort, start_date=date(2020, 1, 1), end_date=date(2022, 12, 31))
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
        assert empty_cohort.additional_criteria.demographic_criteria_list[0].gender is not None

    def test_reset_gender_criteria(self, empty_cohort):
        set_gender_criteria(empty_cohort, GENDER_MALE_CONCEPT_ID)
        reset_gender_criteria(empty_cohort)
        assert len(empty_cohort.additional_criteria.demographic_criteria_list) == 0

    def test_reset_gender_preserves_age(self, empty_cohort):
        set_age_criteria(empty_cohort, min_age=18)
        set_gender_criteria(empty_cohort, GENDER_MALE_CONCEPT_ID)
        reset_gender_criteria(empty_cohort)
        assert len(empty_cohort.additional_criteria.demographic_criteria_list) == 1
        assert empty_cohort.additional_criteria.demographic_criteria_list[0].age is not None

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
        result = (
            set_prior_observation(
                set_post_observation(
                    set_limit_to_first_event(
                        set_cohort_era(empty_cohort, 0)
                    ), 30
                ), 365
            )
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


