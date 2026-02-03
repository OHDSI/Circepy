"""
Tests for cohort expression validator functions.

This module tests both the instance methods on CohortExpression and the
standalone validator functions.
"""

import pytest
import json
from pathlib import Path

from circe.cohortdefinition import (
    CohortExpression,
    PrimaryCriteria,
    ConditionOccurrence,
    DrugExposure,
    InclusionRule,
    CriteriaGroup,
    DateOffsetStrategy,
    CustomEraStrategy,
    ObservationFilter,
    ResultLimit,
)
from circe.cohortdefinition.validators import (
    is_first_event,
    has_exclusion_rules,
    has_inclusion_rule_by_name,
    get_exclusion_count,
    has_censoring_criteria,
    get_censoring_criteria_types,
    has_additional_criteria,
    has_end_strategy,
    get_end_strategy_type,
    get_primary_criteria_types,
    has_observation_window,
    get_primary_limit_type,
    get_concept_set_count,
    has_concept_sets,
)
from circe.vocabulary import ConceptSet


class TestIsFirstEvent:
    """Test is_first_event method and function."""
    
    def test_empty_cohort(self):
        """Test with empty cohort expression."""
        cohort = CohortExpression()
        assert cohort.is_first_event() is False
        assert is_first_event(cohort) is False
    
    def test_no_primary_criteria(self):
        """Test with no primary criteria."""
        cohort = CohortExpression(primary_criteria=None)
        assert cohort.is_first_event() is False
    
    def test_all_first_true(self):
        """Test when all criteria have first=True."""
        criteria1 = ConditionOccurrence(codeset_id=1, first=True)
        criteria2 = DrugExposure(codeset_id=2, first=True)
        
        primary = PrimaryCriteria(criteria_list=[criteria1, criteria2])
        cohort = CohortExpression(primary_criteria=primary)
        
        assert cohort.is_first_event() is True
        assert is_first_event(cohort) is True
    
    def test_all_first_false(self):
        """Test when all criteria have first=False."""
        criteria1 = ConditionOccurrence(codeset_id=1, first=False)
        criteria2 = DrugExposure(codeset_id=2, first=False)
        
        primary = PrimaryCriteria(criteria_list=[criteria1, criteria2])
        cohort = CohortExpression(primary_criteria=primary)
        
        assert cohort.is_first_event() is False
    
    def test_mixed_first_values(self):
        """Test when criteria have mixed first values."""
        criteria1 = ConditionOccurrence(codeset_id=1, first=True)
        criteria2 = DrugExposure(codeset_id=2, first=False)
        
        primary = PrimaryCriteria(criteria_list=[criteria1, criteria2])
        cohort = CohortExpression(primary_criteria=primary)
        
        assert cohort.is_first_event() is False
    
    def test_first_none(self):
        """Test when first is None."""
        criteria1 = ConditionOccurrence(codeset_id=1, first=None)
        
        primary = PrimaryCriteria(criteria_list=[criteria1])
        cohort = CohortExpression(primary_criteria=primary)
        
        assert cohort.is_first_event() is False


class TestExclusionRules:
    """Test exclusion rule methods and functions."""
    
    def test_no_exclusion_rules(self):
        """Test cohort with no exclusion rules."""
        cohort = CohortExpression()
        
        assert cohort.has_exclusion_rules() is False
        assert has_exclusion_rules(cohort) is False
        assert cohort.get_exclusion_count() == 0
        assert get_exclusion_count(cohort) == 0
    
    def test_with_exclusion_rules(self):
        """Test cohort with exclusion rules."""
        rule1 = InclusionRule(name="Rule 1", description="First rule")
        rule2 = InclusionRule(name="Rule 2", description="Second rule")
        
        cohort = CohortExpression(inclusion_rules=[rule1, rule2])
        
        assert cohort.has_exclusion_rules() is True
        assert has_exclusion_rules(cohort) is True
        assert cohort.get_exclusion_count() == 2
        assert get_exclusion_count(cohort) == 2
    
    def test_has_inclusion_rule_by_name(self):
        """Test finding inclusion rule by name."""
        rule1 = InclusionRule(name="Prior Cancer", description="Exclude prior cancer")
        rule2 = InclusionRule(name="Age Limit", description="Age restriction")
        
        cohort = CohortExpression(inclusion_rules=[rule1, rule2])
        
        assert cohort.has_inclusion_rule_by_name("Prior Cancer") is True
        assert has_inclusion_rule_by_name(cohort, "Prior Cancer") is True
        assert cohort.has_inclusion_rule_by_name("Age Limit") is True
        assert cohort.has_inclusion_rule_by_name("Nonexistent") is False
        assert has_inclusion_rule_by_name(cohort, "Nonexistent") is False
    
    def test_has_inclusion_rule_by_name_no_rules(self):
        """Test finding rule by name when no rules exist."""
        cohort = CohortExpression()
        
        assert cohort.has_inclusion_rule_by_name("Any Name") is False


class TestCensoringCriteria:
    """Test censoring criteria methods and functions."""
    
    def test_no_censoring_criteria(self):
        """Test cohort with no censoring criteria."""
        cohort = CohortExpression()
        
        assert cohort.has_censoring_criteria() is False
        assert has_censoring_criteria(cohort) is False
        assert cohort.get_censoring_criteria_types() == []
        assert get_censoring_criteria_types(cohort) == []
    
    def test_with_censoring_criteria(self):
        """Test cohort with censoring criteria."""
        censor1 = ConditionOccurrence(codeset_id=1)
        censor2 = DrugExposure(codeset_id=2)
        
        cohort = CohortExpression(censoring_criteria=[censor1, censor2])
        
        assert cohort.has_censoring_criteria() is True
        assert has_censoring_criteria(cohort) is True
        
        types = cohort.get_censoring_criteria_types()
        assert len(types) == 2
        assert "ConditionOccurrence" in types
        assert "DrugExposure" in types
        
        assert get_censoring_criteria_types(cohort) == types


class TestAdditionalCriteria:
    """Test additional criteria methods and functions."""
    
    def test_no_additional_criteria(self):
        """Test cohort with no additional criteria."""
        cohort = CohortExpression()
        
        assert cohort.has_additional_criteria() is False
        assert has_additional_criteria(cohort) is False
    
    def test_empty_additional_criteria(self):
        """Test cohort with empty additional criteria group."""
        empty_group = CriteriaGroup()
        cohort = CohortExpression(additional_criteria=empty_group)
        
        assert cohort.has_additional_criteria() is False
    
    def test_with_additional_criteria(self):
        """Test cohort with non-empty additional criteria."""
        criteria = ConditionOccurrence(codeset_id=1)
        from circe.cohortdefinition.criteria import CorelatedCriteria
        from circe.cohortdefinition.core import Window
        
        correlated = CorelatedCriteria(criteria=criteria)
        group = CriteriaGroup(criteria_list=[correlated])
        cohort = CohortExpression(additional_criteria=group)
        
        assert cohort.has_additional_criteria() is True
        assert has_additional_criteria(cohort) is True


class TestEndStrategy:
    """Test end strategy methods and functions."""
    
    def test_no_end_strategy(self):
        """Test cohort with no end strategy."""
        cohort = CohortExpression()
        
        assert cohort.has_end_strategy() is False
        assert has_end_strategy(cohort) is False
        assert cohort.get_end_strategy_type() is None
        assert get_end_strategy_type(cohort) is None
    
    def test_date_offset_strategy(self):
        """Test cohort with DateOffset end strategy."""
        strategy = DateOffsetStrategy(offset=30, date_field="StartDate")
        cohort = CohortExpression(end_strategy=strategy)
        
        assert cohort.has_end_strategy() is True
        assert has_end_strategy(cohort) is True
        assert cohort.get_end_strategy_type() == "DateOffset"
        assert get_end_strategy_type(cohort) == "DateOffset"
    
    def test_custom_era_strategy(self):
        """Test cohort with CustomEra end strategy."""
        strategy = CustomEraStrategy(drug_codeset_id=1, gap_days=30, offset=0)
        cohort = CohortExpression(end_strategy=strategy)
        
        assert cohort.has_end_strategy() is True
        assert cohort.get_end_strategy_type() == "CustomEra"
        assert get_end_strategy_type(cohort) == "CustomEra"


class TestPrimaryCriteria:
    """Test primary criteria methods and functions."""
    
    def test_no_primary_criteria(self):
        """Test cohort with no primary criteria."""
        cohort = CohortExpression()
        
        assert cohort.get_primary_criteria_types() == []
        assert get_primary_criteria_types(cohort) == []
        assert cohort.has_observation_window() is False
        assert has_observation_window(cohort) is False
        assert cohort.get_primary_limit_type() is None
        assert get_primary_limit_type(cohort) is None
    
    def test_primary_criteria_types(self):
        """Test getting primary criteria types."""
        criteria1 = ConditionOccurrence(codeset_id=1)
        criteria2 = DrugExposure(codeset_id=2)
        
        primary = PrimaryCriteria(criteria_list=[criteria1, criteria2])
        cohort = CohortExpression(primary_criteria=primary)
        
        types = cohort.get_primary_criteria_types()
        assert len(types) == 2
        assert "ConditionOccurrence" in types
        assert "DrugExposure" in types
        assert get_primary_criteria_types(cohort) == types
    
    def test_observation_window(self):
        """Test observation window detection."""
        obs_window = ObservationFilter(prior_days=365, post_days=0)
        primary = PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
            observation_window=obs_window
        )
        cohort = CohortExpression(primary_criteria=primary)
        
        assert cohort.has_observation_window() is True
        assert has_observation_window(cohort) is True
    
    def test_primary_limit_type(self):
        """Test getting primary limit type."""
        limit = ResultLimit(type="First")
        primary = PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
            primary_limit=limit
        )
        cohort = CohortExpression(primary_criteria=primary)
        
        assert cohort.get_primary_limit_type() == "First"
        assert get_primary_limit_type(cohort) == "First"


class TestConceptSets:
    """Test concept set methods and functions."""
    
    def test_no_concept_sets(self):
        """Test cohort with no concept sets."""
        cohort = CohortExpression()
        
        assert cohort.has_concept_sets() is False
        assert has_concept_sets(cohort) is False
        assert cohort.get_concept_set_count() == 0
        assert get_concept_set_count(cohort) == 0
    
    def test_with_concept_sets(self):
        """Test cohort with concept sets."""
        cs1 = ConceptSet(id=1, name="Diabetes")
        cs2 = ConceptSet(id=2, name="Hypertension")
        
        cohort = CohortExpression(concept_sets=[cs1, cs2])
        
        assert cohort.has_concept_sets() is True
        assert has_concept_sets(cohort) is True
        assert cohort.get_concept_set_count() == 2
        assert get_concept_set_count(cohort) == 2


class TestRealCohortDefinition:
    """Test with real cohort definition from test files."""
    
    def test_isolated_immune_thrombocytopenia(self):
        """Test with the isolated immune thrombocytopenia cohort."""
        test_file = Path(__file__).parent / "cohorts" / "isolated_immune_thrombocytopenia.json"
        
        if not test_file.exists():
            pytest.skip("Test cohort file not found")
        
        with open(test_file) as f:
            data = json.load(f)
        
        cohort = CohortExpression.model_validate(data)
        
        # This cohort should have concept sets
        assert cohort.has_concept_sets() is True
        assert cohort.get_concept_set_count() > 0
        
        # Check primary criteria
        assert len(cohort.get_primary_criteria_types()) > 0
        
        # This cohort has inclusion rules (exclusion criteria)
        assert cohort.has_exclusion_rules() is True
        assert cohort.get_exclusion_count() > 0
