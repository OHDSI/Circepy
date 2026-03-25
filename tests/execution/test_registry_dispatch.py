from __future__ import annotations

import pytest

from circe.cohortdefinition.criteria import Criteria, CriteriaGroup
from circe.execution.errors import UnsupportedCriterionError
from circe.execution.lower.criteria import lower_criterion
from circe.execution.normalize.criteria import NormalizedCriterion, normalize_criterion
from circe.extensions import get_registry, lowerer, normalizer
from circe.extensions.waveform import WaveformOccurrence


class FakeCriteria(Criteria):
    pass


FakeCriteria.model_rebuild(_types_namespace={"CriteriaGroup": CriteriaGroup})


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Ensure the fake criteria gets cleaned up after the test."""
    registry = get_registry()
    yield
    registry._lowerers.pop(FakeCriteria, None)
    registry._normalizers.pop(FakeCriteria, None)


def test_registry_dispatch_round_trip():
    fake_criterion = FakeCriteria()
    fake_normalized = NormalizedCriterion(
        raw_criteria=fake_criterion,
        criterion_type="Fake",
        domain="fake",
        source_table="fake",
        event_id_column="fake_id",
        start_date_column="fake_start",
        end_date_column="fake_end",
        concept_column=None,
        source_concept_column=None,
        visit_occurrence_column=None,
        codeset_id=None,
        first=False,
        occurrence_start_date=None,
        occurrence_end_date=None,
        person_filters=NormalizedCriterion._person_filters_from_criterion(fake_criterion)
        if hasattr(NormalizedCriterion, "_person_filters_from_criterion")
        else None,
    )

    @normalizer(FakeCriteria)
    def fake_normalizer(criteria):
        return fake_normalized

    @lowerer(FakeCriteria)
    def fake_lowerer(criterion, *, criterion_index):
        return "fake_plan_result"

    # Test normalize dispatch
    normalized = normalize_criterion(fake_criterion)
    assert normalized is fake_normalized

    # Test lower dispatch
    plan = lower_criterion(normalized, criterion_index=1)
    assert plan == "fake_plan_result"


def test_unknown_criteria_raises():
    class UnknownCriteria(Criteria):
        pass

    UnknownCriteria.model_rebuild(_types_namespace={"CriteriaGroup": CriteriaGroup})

    with pytest.raises(UnsupportedCriterionError, match="unsupported criterion type UnknownCriteria"):
        normalize_criterion(UnknownCriteria())

    # Create a dummy normalized criterion containing the unknown criteria to test lower_criterion
    fake_normalized = NormalizedCriterion(
        raw_criteria=UnknownCriteria(),
        criterion_type="UnknownCriteria",
        domain="unknown",
        source_table="unknown",
        event_id_column="id",
        start_date_column="start",
        end_date_column="end",
        concept_column=None,
        source_concept_column=None,
        visit_occurrence_column=None,
        codeset_id=None,
        first=False,
        occurrence_start_date=None,
        occurrence_end_date=None,
        person_filters=None,
    )

    with pytest.raises(UnsupportedCriterionError, match="no lowerer registered for UnknownCriteria"):
        lower_criterion(fake_normalized, criterion_index=1)


def test_waveform_extension_dispatch():
    # The extension should have pre-registered its normalizer and lowerer
    waveform = WaveformOccurrence()

    # Check that normalizer is found
    normalized = normalize_criterion(waveform)
    assert normalized.domain == "waveform_occurrence"

    # Check that lowerer is found
    plan = lower_criterion(normalized, criterion_index=1)

    assert plan.source.table_name == "waveform_occurrence"
    assert plan.criterion_type == "WaveformOccurrence"
