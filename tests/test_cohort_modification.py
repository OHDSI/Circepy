"""
Unit tests for cohort modification capabilities.
"""

import pytest
from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition import CohortExpression, InclusionRule
from circe.vocabulary import ConceptSet, Concept


class TestCohortModification:
    """Test cohort modification capabilities."""
    
    def test_from_expression_basic(self):
        """Test loading a cohort from expression."""
        # Build a simple cohort
        expr = (CohortBuilder("Original Cohort")
                .with_condition(1)
                .first_occurrence()
                .with_observation(prior_days=365)
                .build())
        
        # Load it for modification
        builder = CohortBuilder.from_expression(expr)
        
        # Verify it loaded correctly
        assert builder._title == "Original Cohort"
        assert builder._state is not None
        assert len(builder._state._entry_configs) == 1
        assert builder._state._prior_observation == 365
    
    def test_from_expression_with_new_title(self):
        """Test loading with a new title."""
        expr = (CohortBuilder("Original")
                .with_drug(2)
                .build())
        
        builder = CohortBuilder.from_expression(expr, title="Modified")
        assert builder._title == "Modified"
    
    def test_from_expression_preserves_concept_sets(self):
        """Test that concept sets are preserved."""
        cs = ConceptSet(id=1, name="Test Concept Set")
        
        expr = (CohortBuilder("Test")
                .with_concept_sets(cs)
                .with_condition(1)
                .build())
        
        builder = CohortBuilder.from_expression(expr)
        assert len(builder._concept_sets) == 1
        assert builder._concept_sets[0].id == 1
    
    def test_from_expression_no_primary_criteria_raises(self):
        """Test that loading without primary criteria raises error."""
        # Create an invalid expression manually
        expr = CohortExpression(title="Invalid")
        
        with pytest.raises(ValueError, match="Cannot modify cohort without primary criteria"):
            CohortBuilder.from_expression(expr)
    
    def test_modify_and_add_criteria(self):
        """Test modifying an existing cohort by adding criteria."""
        # Create original cohort
        expr = (CohortBuilder("Diabetes")
                .with_condition(1)
                .first_occurrence()
                .build())
        
        # Modify it
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.require_drug(2, within_days_before=30)
            cohort.exclude_condition(3, anytime_before=True)
        
        modified = cohort.expression
        
        # Verify modifications
        assert modified.title == "Diabetes"
        assert len(modified.inclusion_rules) >= 1
    
    def test_remove_inclusion_rule(self):
        """Test removing an inclusion rule by name."""
        # Create cohort with named rules
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .begin_rule("Rule A")
                .require_drug(2, anytime_before=True)
                .end_rule()
                .begin_rule("Rule B")
                .require_measurement(3, same_day=True)
                .end_rule()
                .build())
        
        # Remove Rule A
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.remove_inclusion_rule("Rule A")
        
        modified = cohort.expression
        rule_names = [r.name for r in modified.inclusion_rules]
        
        assert "Rule A" not in rule_names
        assert "Rule B" in rule_names
    
    def test_remove_inclusion_rule_invalid_name_raises(self):
        """Test that removing non-existent rule raises KeyError."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .build())
        
        with pytest.raises(KeyError, match="No inclusion rule found"):
            with CohortBuilder.from_expression(expr) as cohort:
                cohort.remove_inclusion_rule("Nonexistent Rule")
    
    def test_remove_censoring_criteria_by_type(self):
        """Test removing censoring criteria by type."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .censor_on_drug(2, anytime_after=True)
                .censor_on_death()
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.remove_censoring_criteria(criteria_type="Death")
        
        modified = cohort.expression
        
        # Should have one censoring criteria left (drug)
        assert len(modified.censoring_criteria) == 1
        assert modified.censoring_criteria[0].__class__.__name__ == "DrugExposure"
    
    def test_remove_censoring_criteria_by_concept_set(self):
        """Test removing censoring criteria by concept set ID."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .censor_on_drug(2, anytime_after=True)
                .censor_on_condition(3, anytime_after=True)
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.remove_censoring_criteria(concept_set_id=2)
        
        modified = cohort.expression
        
        # Should have one censoring criteria left (condition with cs_id=3)
        assert len(modified.censoring_criteria) == 1
        assert modified.censoring_criteria[0].codeset_id == 3
    
    def test_remove_censoring_criteria_by_index(self):
        """Test removing censoring criteria by index."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .censor_on_drug(2, anytime_after=True)
                .censor_on_condition(3, anytime_after=True)
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.remove_censoring_criteria(index=0)
        
        modified = cohort.expression
        
        # Should have one censoring criteria left
        assert len(modified.censoring_criteria) == 1
    
    def test_remove_censoring_criteria_no_args_raises(self):
        """Test that calling without arguments raises ValueError."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .build())
        
        with pytest.raises(ValueError, match="Must provide one of"):
            with CohortBuilder.from_expression(expr) as cohort:
                cohort.remove_censoring_criteria()
    
    def test_remove_censoring_criteria_multiple_args_raises(self):
        """Test that providing multiple arguments raises ValueError."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .build())
        
        with pytest.raises(ValueError, match="Can only provide one of"):
            with CohortBuilder.from_expression(expr) as cohort:
                cohort.remove_censoring_criteria(criteria_type="Death", index=0)
    
    def test_remove_entry_event_by_concept_set(self):
        """Test removing an entry event by concept set ID."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .or_with_drug(2)
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.remove_entry_event(concept_set_id=1)
        
        modified = cohort.expression
        
        # Should have one entry event left (drug)
        assert len(modified.primary_criteria.criteria_list) == 1
        assert modified.primary_criteria.criteria_list[0].__class__.__name__ == "DrugExposure"
    
    def test_remove_entry_event_by_type(self):
        """Test removing an entry event by type."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .or_with_drug(2)
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.remove_entry_event(criteria_type="ConditionOccurrence")
        
        modified = cohort.expression
        
        # Should have one entry event left (drug)
        assert len(modified.primary_criteria.criteria_list) == 1
        assert modified.primary_criteria.criteria_list[0].__class__.__name__ == "DrugExposure"
    
    def test_remove_last_entry_event_raises(self):
        """Test that removing the last entry event raises ValueError."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .build())
        
        with pytest.raises(ValueError, match="Cannot remove the last entry event"):
            with CohortBuilder.from_expression(expr) as cohort:
                cohort.remove_entry_event(concept_set_id=1)
    
    def test_remove_concept_set(self):
        """Test removing a concept set by ID."""
        cs1 = ConceptSet(id=1, name="CS1")
        cs2 = ConceptSet(id=2, name="CS2")
        
        expr = (CohortBuilder("Test")
                .with_concept_sets(cs1, cs2)
                .with_condition(1)
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.remove_concept_set(concept_set_id=1)
        
        modified = cohort.expression
        
        assert len(modified.concept_sets) == 1
        assert modified.concept_sets[0].id == 2
    
    def test_remove_concept_set_invalid_id_raises(self):
        """Test that removing non-existent concept set raises KeyError."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .build())
        
        with pytest.raises(KeyError, match="No concept set found"):
            with CohortBuilder.from_expression(expr) as cohort:
                cohort.remove_concept_set(concept_set_id=999)
    
    def test_remove_all_references(self):
        """Test removing a concept set and all references."""
        cs1 = ConceptSet(id=1, name="CS1")
        cs2 = ConceptSet(id=2, name="CS2")
        
        expr = (CohortBuilder("Test")
                .with_concept_sets(cs1, cs2)
                .with_condition(1)
                .or_with_drug(2)
                .require_measurement(1, same_day=True)  # References cs1
                .censor_on_condition(1, anytime_after=True)  # References cs1
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.remove_all_references(concept_set_id=1)
        
        modified = cohort.expression
        
        # Concept set should be removed
        assert len(modified.concept_sets) == 1
        assert modified.concept_sets[0].id == 2
        
        # Entry event with cs1 should be removed
        assert len(modified.primary_criteria.criteria_list) == 1
        assert modified.primary_criteria.criteria_list[0].codeset_id == 2
        
        # Censoring criteria with cs1 should be removed
        assert len(modified.censoring_criteria) == 0
    
    def test_clear_inclusion_rules(self):
        """Test clearing all inclusion rules."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .require_drug(2, within_days_before=30)
                .exclude_condition(3, anytime_before=True)
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.clear_inclusion_rules()
        
        modified = cohort.expression
        
        # Should have only the default empty rule
        assert len(modified.inclusion_rules) <= 1
        if modified.inclusion_rules:
            assert modified.inclusion_rules[0].name == "Inclusion Criteria"
    
    def test_clear_censoring_criteria(self):
        """Test clearing all censoring criteria."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .censor_on_drug(2, anytime_after=True)
                .censor_on_death()
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.clear_censoring_criteria()
        
        modified = cohort.expression
        assert len(modified.censoring_criteria) == 0
    
    def test_clear_demographic_criteria(self):
        """Test clearing demographic restrictions."""
        expr = (CohortBuilder("Test")
                .with_condition(1)
                .min_age(18)
                .max_age(65)
                .require_gender(8507, 8532)  # Male, Female
                .build())
        
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.clear_demographic_criteria()
        
        modified = cohort.expression
        
        # Demographic rule should be removed or empty
        demo_rules = [r for r in modified.inclusion_rules if r.name == "Demographic Criteria"]
        assert len(demo_rules) == 0
    
    def test_complex_modification_workflow(self):
        """Test a realistic workflow with multiple modifications."""
        # Create original cohort
        cs1 = ConceptSet(id=1, name="Diabetes")
        cs2 = ConceptSet(id=2, name="Metformin")
        cs3 = ConceptSet(id=3, name="Cancer")
        
        expr = (CohortBuilder("Diabetes Cohort")
                .with_concept_sets(cs1, cs2, cs3)
                .with_condition(1)
                .first_occurrence()
                .with_observation(prior_days=365)
                .min_age(18)
                .begin_rule("Prior Treatment")
                .require_drug(2, within_days_before=365)
                .end_rule()
                .begin_rule("Cancer Exclusion")
                .exclude_condition(3, anytime_before=True)
                .end_rule()
                .build())
        
        # Modify it
        cs4 = ConceptSet(id=4, name="Insulin")
        
        with CohortBuilder.from_expression(expr) as cohort:
            # Remove old exclusion rule
            cohort.remove_inclusion_rule("Cancer Exclusion")
            
            # Add new concept set
            cohort.with_concept_sets(cs4)
            
            # Add new criteria
            cohort.require_measurement(4, within_days_after=90)
            
            # Clear age restriction
            cohort.clear_demographic_criteria()
        
        modified = cohort.expression
        
        # Verify changes
        assert modified.title == "Diabetes Cohort"
        assert len(modified.concept_sets) == 4
        
        rule_names = [r.name for r in modified.inclusion_rules]
        assert "Prior Treatment" in rule_names
        assert "Cancer Exclusion" not in rule_names
        
        # Demographic criteria should be cleared
        demo_rules = [r for r in modified.inclusion_rules if r.name == "Demographic Criteria"]
        assert len(demo_rules) == 0
    
    def test_modification_preserves_original(self):
        """Test that modifications don't affect the original expression."""
        # Create original
        expr = (CohortBuilder("Original")
                .with_condition(1)
                .require_drug(2, within_days_before=30)
                .build())
        
        original_rule_count = len(expr.inclusion_rules)
        
        # Modify copy
        with CohortBuilder.from_expression(expr) as cohort:
            cohort.clear_inclusion_rules()
            cohort.require_measurement(3, same_day=True)
        
        # Original should be unchanged
        assert len(expr.inclusion_rules) == original_rule_count
