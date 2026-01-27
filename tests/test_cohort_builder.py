"""
Unit tests for the Simplified Parameter-Based Fluent Builder.
"""

import pytest
from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition import CohortExpression


# =============================================================================
# CONTEXT MANAGER TESTS
# =============================================================================

class TestContextManager:
    """Test the context manager API for CohortBuilder."""
    
    def test_context_manager_basic(self):
        """Test basic context manager usage."""
        with CohortBuilder("Context Test") as cohort:
            cohort.with_condition(1)
        
        # After exiting, expression should be built
        expr = cohort.expression
        assert isinstance(expr, CohortExpression)
        assert expr.title == "Context Test"
    
    def test_context_manager_auto_builds(self):
        """Verify that auto-build happens on context exit."""
        with CohortBuilder("Auto Build Test") as cohort:
            cohort.with_drug(2)
            cohort.first_occurrence()
            cohort.with_observation_window(prior_days=365)
        
        expr = cohort.expression
        assert expr.primary_criteria.observation_window.prior_days == 365
    
    def test_context_manager_with_criteria(self):
        """Test context manager with inclusion/exclusion criteria."""
        with CohortBuilder("Criteria Test") as cohort:
            cohort.with_condition(1)
            cohort.require_drug(2, within_days_before=30)
            cohort.exclude_condition(3, anytime_before=True)
        
        expr = cohort.expression
        assert expr.inclusion_rules is not None
        assert len(expr.inclusion_rules) >= 1
    
    def test_context_manager_result_access_before_exit_raises(self):
        """Accessing expression inside context should raise."""
        with pytest.raises(RuntimeError, match="inside the context manager"):
            with CohortBuilder("Error Test") as cohort:
                cohort.with_condition(1)
                _ = cohort.expression  # Should raise
    
    def test_context_manager_no_entry_event_raises(self):
        """Accessing expression with no entry event should raise."""
        with CohortBuilder("Empty Test") as cohort:
            pass  # No entry event defined
        
        with pytest.raises(RuntimeError, match="No cohort has been built"):
            _ = cohort.expression
    
    def test_context_manager_nested_rules(self):
        """Test nested inclusion rule contexts."""
        with CohortBuilder("Nested Rules Test") as cohort:
            cohort.with_condition(1)
            
            with cohort.include_rule("Prior Treatment") as rule:
                rule.require_drug(2, anytime_before=True)
            
            with cohort.include_rule("Lab Confirmation") as rule:
                rule.require_measurement(3, same_day=True)
        
        expr = cohort.expression
        # Should have two named rules
        rule_names = [r.name for r in expr.inclusion_rules]
        assert "Prior Treatment" in rule_names
        assert "Lab Confirmation" in rule_names
    
    def test_context_manager_exception_still_builds(self):
        """Even if an exception occurs, the cohort should be built if possible."""
        cohort = CohortBuilder("Exception Test")
        try:
            with cohort:
                cohort.with_condition(1)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Cohort should still be built
        expr = cohort.expression
        assert isinstance(expr, CohortExpression)
    
    def test_context_manager_chaining_returns_self(self):
        """Context manager methods should return self for chaining."""
        with CohortBuilder("Chaining Test") as cohort:
            result = cohort.with_condition(1)
            assert result is cohort
            
            result = cohort.first_occurrence()
            assert result is cohort
            
            result = cohort.require_drug(2, within_days_before=30)
            assert result is cohort


# =============================================================================
# FLUENT API TESTS (Backwards Compatibility)
# =============================================================================


class TestCohortStart:
    """Test initial Cohort state."""
    
    def test_create_cohort(self):
        cohort = CohortBuilder("Test Cohort")
        assert cohort._title == "Test Cohort"
    
    def test_with_condition_returns_entry_state(self):
        result = CohortBuilder("Test").with_condition(concept_set_id=1)
        assert hasattr(result, 'first_occurrence')
        assert hasattr(result, 'with_observation')
        assert hasattr(result, 'build')
    
    def test_with_drug_returns_entry_state(self):
        result = CohortBuilder("Test").with_drug(concept_set_id=1)
        assert hasattr(result, 'first_occurrence')


class TestCohortWithEntry:
    """Test CohortWithEntry state."""
    
    def test_first_occurrence_chainable(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .first_occurrence())
        assert result._entry_queries[0]._get_config().first_occurrence is True
    
    def test_with_observation(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .with_observation(prior_days=365, post_days=30))
        assert result._prior_observation_days == 365
        assert result._post_observation_days == 30
    
    def test_min_age(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .min_age(18))
        assert result._entry_queries[0]._get_config().age_min == 18
    
    def test_build_from_entry(self):
        expr = (CohortBuilder("Simple")
                .with_condition(1)
                .build())
        assert isinstance(expr, CohortExpression)
        assert expr.title == "Simple"


class TestCohortWithCriteria:
    """Test CohortWithCriteria state."""
    
    def test_require_returns_criteria_state(self):
        # In new API, require_drug returns ChoiceWithCriteria directly if params are passed
        result = (CohortBuilder("Test")
                 .with_condition(1)
                 .require_drug(2, anytime_before=True))
        # It returns CohortWithCriteria, so it should have build(), require_*, etc.
        assert hasattr(result, 'require_condition')
        assert hasattr(result, 'build')
    
    def test_chained_criteria(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2, within_days=(0, 30))  # within_days_after(30)
                  .exclude_drug(3, anytime_before=True))
        assert len(result._rules[0]["group"].criteria) == 2


class TestBuildCohortExpression:
    """Test building final CohortExpression."""
    
    def test_simple_cohort(self):
        expr = (CohortBuilder("Simple Cohort")
                .with_condition(1)
                .first_occurrence()
                .with_observation(prior_days=365)
                .build())
        
        assert expr.title == "Simple Cohort"
        assert expr.primary_criteria is not None
        assert expr.primary_criteria.observation_window.prior_days == 365
    
    def test_cohort_with_inclusion(self):
        expr = (CohortBuilder("With Inclusion")
                .with_drug(2)
                .first_occurrence()
                .require_condition(1, within_days_before=365)
                .build())
        
        assert expr.inclusion_rules is not None
        assert len(expr.inclusion_rules) == 1
    
    def test_cohort_with_exclusion(self):
        expr = (CohortBuilder("With Exclusion")
                .with_condition(1)
                .exclude_drug(2, anytime_before=True)
                .build())
        
        assert expr.inclusion_rules is not None
    
    def test_cohort_with_multiple_criteria(self):
        expr = (CohortBuilder("Multiple Criteria")
                .with_drug(2)
                .first_occurrence()
                .with_observation(prior_days=365)
                .min_age(18)
                .require_condition(1, within_days_before=365)
                .exclude_drug(2, within_days_before=365)
                .require_measurement(3, within_days_after=30)
                .build())
        
        assert expr.primary_criteria is not None
        assert expr.inclusion_rules is not None


class TestQueryMethods:
    """Test query configuration via parameters."""
    
    def test_within_days_before(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2, within_days_before=365))
        
        config = result._rules[0]["group"].criteria[0].query_config
        assert config.time_window.days_before == 365
        assert config.time_window.days_after == 0
    
    def test_within_days_after(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2, within_days_after=30))
        
        config = result._rules[0]["group"].criteria[0].query_config
        assert config.time_window.days_before == 0
        assert config.time_window.days_after == 30
    
    def test_anytime_before(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .exclude_drug(2, anytime_before=True))
        
        config = result._rules[0]["group"].criteria[0].query_config
        assert config.time_window.days_before == 99999
    
    def test_same_day(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2, same_day=True))
        
        config = result._rules[0]["group"].criteria[0].query_config
        assert config.time_window.days_before == 0
        assert config.time_window.days_after == 0


def test_begin_end_rule():
    """Test that begin_rule and end_rule work correctly."""
    cohort = (
        CohortBuilder("Test Rule Blocks")
        .with_condition(1)
        .begin_rule("Rule A")
        .require_drug(2, anytime_before=True)
        .end_rule()
        .begin_rule("Rule B")
        .require_measurement(3, same_day=True)
        .end_rule()
        .build()
    )
    
    # Inclusion rules should be "Rule A" and "Rule B"
    # (The default "Inclusion Criteria" rule is skipped because it's empty)
    assert cohort.inclusion_rules[0].name == "Rule A"
    assert cohort.inclusion_rules[1].name == "Rule B"
