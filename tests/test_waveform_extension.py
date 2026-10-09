"""
Tests for the waveform extension's decorator-based auto-registration.

Verifies that importing extensions.waveform is sufficient to register all four
criteria classes, SQL builders, and markdown templates with the global registry.
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the extension — this is the only step an extension author needs.
# All registrations happen via decorators at import time.
# ---------------------------------------------------------------------------
import circe.extensions.waveform  # noqa: F401  triggers all decorators
from circe.extensions import get_registry
from circe.extensions.waveform.builders.waveform_channel_metadata import WaveformChannelMetadataSqlBuilder
from circe.extensions.waveform.builders.waveform_feature import WaveformFeatureSqlBuilder
from circe.extensions.waveform.builders.waveform_occurrence import WaveformOccurrenceSqlBuilder
from circe.extensions.waveform.builders.waveform_registry import WaveformRegistrySqlBuilder
from circe.extensions.waveform.criteria import (
    WaveformChannelMetadata,
    WaveformFeature,
    WaveformOccurrence,
    WaveformRegistry,
)

# ---------------------------------------------------------------------------
# Criteria class registration
# ---------------------------------------------------------------------------


class TestCriteriaClassRegistration:
    """@criteria_class decorator registers each class by its JSON key."""

    @pytest.mark.parametrize(
        "name, expected_cls",
        [
            ("WaveformOccurrence", WaveformOccurrence),
            ("WaveformRegistry", WaveformRegistry),
            ("WaveformChannelMetadata", WaveformChannelMetadata),
            ("WaveformFeature", WaveformFeature),
        ],
    )
    def test_criteria_class_registered(self, name, expected_cls):
        reg = get_registry()
        assert reg.get_criteria_class(name) is expected_cls

    def test_unregistered_name_returns_none(self):
        reg = get_registry()
        assert reg.get_criteria_class("NonExistentCriteria") is None


# ---------------------------------------------------------------------------
# SQL builder registration
# ---------------------------------------------------------------------------


class TestSqlBuilderRegistration:
    """@sql_builder decorator maps each criteria type to the right builder."""

    @pytest.mark.parametrize(
        "criteria_cls, expected_builder_cls",
        [
            (WaveformOccurrence, WaveformOccurrenceSqlBuilder),
            (WaveformRegistry, WaveformRegistrySqlBuilder),
            (WaveformChannelMetadata, WaveformChannelMetadataSqlBuilder),
            (WaveformFeature, WaveformFeatureSqlBuilder),
        ],
    )
    def test_builder_returned_for_criteria_instance(self, criteria_cls, expected_builder_cls):
        reg = get_registry()
        instance = criteria_cls()
        builder = reg.get_builder(instance)
        assert builder is not None
        assert isinstance(builder, expected_builder_cls)


# ---------------------------------------------------------------------------
# Markdown template registration
# ---------------------------------------------------------------------------


class TestMarkdownTemplateRegistration:
    """@markdown_template decorator maps each criteria type to its .j2 file."""

    @pytest.mark.parametrize(
        "criteria_cls, expected_template",
        [
            (WaveformOccurrence, "waveform_occurrence.j2"),
            (WaveformRegistry, "waveform_registry.j2"),
            (WaveformChannelMetadata, "waveform_channel_metadata.j2"),
            (WaveformFeature, "waveform_feature.j2"),
        ],
    )
    def test_template_registered(self, criteria_cls, expected_template):
        reg = get_registry()
        instance = criteria_cls()
        assert reg.get_template(instance) == expected_template


# ---------------------------------------------------------------------------
# Template path registration
# ---------------------------------------------------------------------------


class TestTemplatePathRegistration:
    """template_path() call in __init__.py adds the templates directory."""

    def test_template_directory_registered(self):
        reg = get_registry()
        expected = Path(circe.extensions.waveform.__file__).parent / "templates"
        assert expected in reg.template_paths

    def test_template_files_exist(self):
        expected = Path(circe.extensions.waveform.__file__).parent / "templates"
        for name in [
            "waveform_occurrence.j2",
            "waveform_registry.j2",
            "waveform_channel_metadata.j2",
            "waveform_feature.j2",
        ]:
            assert (expected / name).exists(), f"Missing template: {name}"
