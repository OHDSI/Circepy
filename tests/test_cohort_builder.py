"""
Unit tests for the State-Based Fluent Builder.

Tests the Cohort -> CohortWithEntry -> CohortWithCriteria progression.
"""

import pytest
from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition import CohortExpression


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
    
    def test_with_measurement_returns_entry_state(self):
        result = CohortBuilder("Test").with_measurement(concept_set_id=1)
        assert hasattr(result, 'first_occurrence')
    
    def test_with_procedure_returns_entry_state(self):
        result = CohortBuilder("Test").with_procedure(concept_set_id=1)
        assert hasattr(result, 'first_occurrence')


class TestCohortWithEntry:
    """Test CohortWithEntry state."""
    
    def test_first_occurrence_chainable(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .first_occurrence())
        assert result._entry_config.first_occurrence is True
    
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
        assert result._entry_config.age_min == 18
    
    def test_build_from_entry(self):
        expr = (CohortBuilder("Simple")
                .with_condition(1)
                .build())
        assert isinstance(expr, CohortExpression)
        assert expr.title == "Simple"


class TestCohortWithCriteria:
    """Test CohortWithCriteria state."""
    
    def test_require_transitions_to_query(self):
        query = (CohortBuilder("Test")
                 .with_condition(1)
                 .require_drug(2))
        assert hasattr(query, 'within_days_before')
        assert hasattr(query, 'anytime_before')
    
    def test_exclude_transitions_to_query(self):
        query = (CohortBuilder("Test")
                 .with_condition(1)
                 .exclude_drug(2))
        assert hasattr(query, 'within_days_before')
    
    def test_query_within_days_returns_criteria_state(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2)
                  .within_days_before(365))
        assert hasattr(result, 'require_condition')
        assert hasattr(result, 'exclude_drug')
        assert hasattr(result, 'build')
    
    def test_chained_criteria(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2).within_days_after(30)
                  .exclude_drug(3).anytime_before())
        assert len(result._criteria) == 2


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
                .require_condition(1).within_days_before(365)
                .build())
        
        assert expr.inclusion_rules is not None
        assert len(expr.inclusion_rules) == 1
    
    def test_cohort_with_exclusion(self):
        expr = (CohortBuilder("With Exclusion")
                .with_condition(1)
                .exclude_drug(2).anytime_before()
                .build())
        
        assert expr.inclusion_rules is not None
    
    def test_cohort_with_multiple_criteria(self):
        expr = (CohortBuilder("Multiple Criteria")
                .with_drug(2)
                .first_occurrence()
                .with_observation(prior_days=365)
                .min_age(18)
                .require_condition(1).within_days_before(365)
                .exclude_drug(2).within_days_before(365)
                .require_measurement(3).within_days_after(30)
                .build())
        
        assert expr.primary_criteria is not None
        assert expr.inclusion_rules is not None


class TestQueryMethods:
    """Test query builder methods."""
    
    def test_within_days_before(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2)
                  .within_days_before(365))
        
        config = result._criteria[0].query_config
        assert config.time_window.days_before == 365
        assert config.time_window.days_after == 0
    
    def test_within_days_after(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2)
                  .within_days_after(30))
        
        config = result._criteria[0].query_config
        assert config.time_window.days_before == 0
        assert config.time_window.days_after == 30
    
    def test_anytime_before(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .exclude_drug(2)
                  .anytime_before())
        
        config = result._criteria[0].query_config
        assert config.time_window.days_before == 99999
    
    def test_same_day(self):
        result = (CohortBuilder("Test")
                  .with_condition(1)
                  .require_drug(2)
                  .same_day())
        
        config = result._criteria[0].query_config
        assert config.time_window.days_before == 0
        assert config.time_window.days_after == 0
