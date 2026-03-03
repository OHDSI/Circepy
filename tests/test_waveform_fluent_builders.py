"""Tests for dynamic extension support in fluent builders.

Verifies that the @register_criteria decorator + __getattr__ system
allows extension domains to be used in CohortBuilder, EvaluationBuilder,
and CriteriaGroupBuilder without manual registration of BaseQuery subclasses.
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from circe.extensions import get_registry, _snake_to_pascal, _pascal_to_snake

# Import waveform criteria (triggers @register_criteria decorators)
from waveform_extension.criteria import (
    WaveformOccurrence, WaveformRegistry, WaveformChannelMetadata, WaveformFeature
)
import waveform_extension
waveform_extension.register()

from circe.cohort_builder.builder import CohortBuilder
from circe.evaluation.builder import EvaluationBuilder
from circe.vocabulary import ConceptSet, Concept


def _make_cs(cs_id, name, concept_id):
    return ConceptSet(
        id=cs_id, name=name,
        expression={"items": [{"concept": {"CONCEPT_ID": concept_id, "CONCEPT_NAME": name}}]}
    )


# =============================================================================
# Test: @register_criteria decorator
# =============================================================================

class TestRegisterCriteriaDecorator:

    def test_waveform_criteria_have_circe_domain(self):
        assert WaveformOccurrence._circe_domain == 'WaveformOccurrence'
        assert WaveformFeature._circe_domain == 'WaveformFeature'

    def test_waveform_criteria_have_query_class(self):
        query_cls = WaveformOccurrence._circe_query_class
        assert query_cls.__name__ == 'WaveformOccurrenceQuery'

    def test_waveform_criteria_registered_in_registry(self):
        dq = get_registry().get_domain_query_map()
        for name in ('WaveformOccurrence', 'WaveformRegistry', 'WaveformChannelMetadata', 'WaveformFeature'):
            assert name in dq

    def test_auto_generated_query_sets_domain(self):
        q = WaveformFeature._circe_query_class(concept_set_id=1)
        assert q._config.domain == 'WaveformFeature'
        assert q._config.concept_set_id == 1

    def test_auto_generated_query_extra_fields(self):
        from circe.cohortdefinition.core import NumericRange
        q = WaveformFeature._circe_query_class(concept_set_id=1)
        val_range = NumericRange(value=60, op='gte')
        q.apply_params(value_as_number=val_range)
        assert q._config.extra_fields['value_as_number'] == val_range


# =============================================================================
# Test: CohortBuilder with waveform extension
# =============================================================================

class TestCohortBuilderExtensions:

    def _builder_with_cs(self, *cs_args):
        """Helper to create a CohortBuilder with concept sets."""
        cb = CohortBuilder("Test Cohort")
        for args in cs_args:
            cb.with_concept_sets(_make_cs(*args))
        return cb

    def test_with_waveform_occurrence_entry(self):
        cb = self._builder_with_cs((0, "ECG", 2000000001))
        result = cb.with_waveform_occurrence(0)
        assert hasattr(result, 'build')
        expr = result.build()
        assert len(expr.primary_criteria.criteria_list) == 1
        assert isinstance(expr.primary_criteria.criteria_list[0], WaveformOccurrence)

    def test_require_waveform_feature_inclusion(self):
        cb = self._builder_with_cs((0, "ECG", 2000000001), (1, "HR", 3027018))
        expr = cb.with_waveform_occurrence(0).require_waveform_feature(1, anytime_before=True).build()
        assert len(expr.inclusion_rules) > 0
        corr = expr.inclusion_rules[0].expression.criteria_list[0]
        assert isinstance(corr.criteria, WaveformFeature)

    def test_exclude_waveform_occurrence(self):
        cb = self._builder_with_cs((0, "ECG", 2000000001), (1, "Bad", 2000000002))
        expr = cb.with_waveform_occurrence(0).exclude_waveform_occurrence(1, anytime_before=True).build()
        assert len(expr.inclusion_rules) > 0
        corr = expr.inclusion_rules[0].expression.criteria_list[0]
        assert isinstance(corr.criteria, WaveformOccurrence)
        assert corr.occurrence.count == 0  # Exclusion: exactly 0 occurrences

    def test_unknown_domain_raises_attribute_error(self):
        cb = CohortBuilder("Test")
        with pytest.raises(AttributeError, match="has no attribute"):
            cb.with_nonexistent_domain(0)

    def test_criteria_group_builder_extension(self):
        cb = self._builder_with_cs((0, "ECG", 2000000001), (1, "HR", 3027018))
        expr = (
            cb.with_waveform_occurrence(0)
            .any_of()
                .waveform_feature(1)
            .end_group()
            .build()
        )
        assert len(expr.inclusion_rules) > 0

    def test_build_produces_valid_json(self):
        cb = self._builder_with_cs((0, "ECG", 2000000001))
        expr = cb.with_waveform_occurrence(0).build()
        data = json.loads(expr.model_dump_json(by_alias=True, exclude_none=True))
        assert 'PrimaryCriteria' in data
        assert len(data['PrimaryCriteria']['CriteriaList']) == 1


# =============================================================================
# Test: EvaluationBuilder with waveform extension
# =============================================================================

class TestEvaluationBuilderExtensions:

    def test_waveform_feature_rule(self):
        ev = EvaluationBuilder("Waveform QC")
        hr_id = ev.concept_set("Heart Rate", 3027018)
        ev.add_rule("High HR", weight=10).waveform_feature(hr_id).at_least(1)
        rubric = ev.build()
        assert len(rubric.rules) == 1
        assert rubric.rules[0].name == "High HR"
        corr = rubric.rules[0].expression.criteria_list[0]
        assert isinstance(corr.criteria, WaveformFeature)

    def test_unknown_domain_raises_on_rule_builder(self):
        ev = EvaluationBuilder("Test")
        rule = ev.add_rule("Test Rule", weight=1)
        with pytest.raises(AttributeError, match="has no attribute"):
            rule.nonexistent_domain(1)


# =============================================================================
# Test: Helper functions
# =============================================================================

class TestHelperFunctions:
    def test_snake_to_pascal(self):
        assert _snake_to_pascal('waveform_feature') == 'WaveformFeature'
        assert _snake_to_pascal('condition_occurrence') == 'ConditionOccurrence'
        assert _snake_to_pascal('death') == 'Death'

    def test_pascal_to_snake(self):
        assert _pascal_to_snake('WaveformFeature') == 'waveform_feature'
        assert _pascal_to_snake('ConditionOccurrence') == 'condition_occurrence'
        assert _pascal_to_snake('Death') == 'death'
