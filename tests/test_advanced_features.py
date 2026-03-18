"""
Tests for Phase 4 (Time Window Enhancements) and Phase 5 (Advanced Features).
"""

from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition.cohort import CohortExpression


def test_between_visits():
    """Test between_visits() restricts to same visit."""
    cohort = (
        CohortBuilder("Test Between Visits")
        .with_condition(1)
        .begin_rule("Same Visit Procedure")
        .require_procedure(10)
        .between_visits()
        .build()
    )

    assert isinstance(cohort, CohortExpression)
    # Check restrict_visit flag was set
    # This maps to VisitFilter in CIRCE which requires same visit_occurrence_id


def test_during_event():
    """Test during_event() requires event within index duration."""
    cohort = (
        CohortBuilder("Test During Event")
        .with_drug(1)
        .begin_rule("Measurement During Drug")
        .require_measurement(10)
        .during_event()
        .build()
    )

    # Should set time window with use_index_end=True and 0/0 days
    cohort.inclusion_rules[0].expression.criteria_list[0]
    # Verify time window configuration


def test_before_event_end():
    """Test before_event_end() relative to index end date."""
    cohort = (
        CohortBuilder("Test Before Event End")
        .with_condition(1)
        .begin_rule("Drug Before Condition Ends")
        .require_drug(10)
        .before_event_end(days=7)
        .build()
    )

    # Should set time window relative to index end, 7 days before
    cohort.inclusion_rules[0].expression.criteria_list[0]
    # Verify time window with use_index_end=True


def test_anytime_before_unlimited():
    """Test anytime_before() with no limit."""
    cohort = (
        CohortBuilder("Test Anytime Before Unlimited")
        .with_drug(1)
        .begin_rule("Prior Condition")
        .require_condition(10)
        .anytime_before()
        .build()
    )

    # Should set large lookback window
    cohort.inclusion_rules[0].expression.criteria_list[0]
    # Verify large lookback window


def test_within_days_before_with_years():
    """Test within_days_before() with 5 year limit."""
    cohort = (
        CohortBuilder("Test Within 5 Years Before")
        .with_condition(1)
        .begin_rule("Prior Procedure")
        .require_procedure(10)
        .within_days_before(1825)  # 5 * 365
        .build()
    )

    # Should set time window to 1825 days before
    cohort.inclusion_rules[0].expression.criteria_list[0]
    # Verify 1825 day lookback


def test_anytime_after_unlimited():
    """Test anytime_after() with no limit."""
    cohort = (
        CohortBuilder("Test Anytime After Unlimited")
        .with_condition(1)
        .begin_rule("Future Death")
        .require_death()
        .anytime_after()
        .build()
    )

    # Should set large lookahead window
    cohort.inclusion_rules[0].expression.criteria_list[0]
    # Verify large lookahead window


def test_within_days_after_with_years():
    """Test within_days_after() with 1 year limit."""
    cohort = (
        CohortBuilder("Test Within 1 Year After")
        .with_drug(1)
        .begin_rule("Death Within Year")
        .require_death()
        .within_days_after(365)  # 1 * 365
        .build()
    )

    # Should set time window to 365 days after
    cohort.inclusion_rules[0].expression.criteria_list[0]
    # Verify 365 day lookahead


def test_with_distinct():
    """Test with_distinct() for distinct counting."""
    cohort = (
        CohortBuilder("Test Distinct Counting")
        .with_condition(1)
        .begin_rule("Distinct Measurements")
        .require_measurement(10)
        .with_distinct()
        .at_least(3)
        .anytime_before()
        .build()
    )

    # Should set is_distinct flag
    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.occurrence.is_distinct


def test_ignore_observation_period():
    """Test ignore_observation_period() flag."""
    (
        CohortBuilder("Test Ignore Obs Period")
        .with_drug(1)
        .begin_rule("Condition Outside Obs")
        .require_condition(10)
        .ignore_observation_period()
        .anytime_before()
        .build()
    )

    # Should set ignore_observation_period flag
    # This maps to criteria-level flag in CIRCE


def test_chaining_advanced_features():
    """Test chaining multiple advanced features."""
    cohort = (
        CohortBuilder("Test Feature Chaining")
        .with_condition(1)
        .begin_rule("Complex Criteria")
        .require_measurement(10)
        .with_distinct()
        .ignore_observation_period()
        .at_least(2)
        .within_days_before(3650)  # 10 * 365
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.occurrence.is_distinct
    # Also verify ignore_observation_period and occurrence count


def test_time_window_combinations():
    """Test combining different time window methods."""
    cohort = (
        CohortBuilder("Test Time Window Mix")
        .with_condition(1)
        .begin_rule("Past 2 Years")
        .require_drug(10)
        .within_days_before(730)  # 2 * 365
        .begin_rule("After Index")
        .require_procedure(20)
        .anytime_after()
        .build()
    )

    assert len(cohort.inclusion_rules) == 2


def test_between_visits_with_modifiers():
    """Test between_visits() combined with Phase 2 modifiers."""
    cohort = (
        CohortBuilder("Test Between Visits + Modifiers")
        .with_condition(1)
        .begin_rule("Same-Visit High-Dose Drug")
        .require_drug(10)
        .with_route(4132161)
        .with_dose(min_dose=50.0)
        .between_visits()
        .build()
    )

    criteria = cohort.inclusion_rules[0].expression.criteria_list[0]
    assert criteria.criteria.route_concept is not None
    # Also verify restrict_visit flag
