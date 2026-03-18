"""
Tests for dynamic ibis execution builder registration via the extension registry.

Verifies that:
1. The @ibis_builder decorator registers builders in both the extension registry
   and the low-level execution registry.
2. ExtensionRegistry.register_ibis_builder works for programmatic registration.
3. get_builder falls back to the extension registry when a criteria name is not
   in the module-level _REGISTRY.
4. No hardcoding of waveform or other extension types is required.
"""

import pytest

from circe.cohortdefinition.criteria import Criteria
from circe.execution.builders.registry import _REGISTRY, get_builder
from circe.extensions import get_registry, ibis_builder

# ---------------------------------------------------------------------------
# Decorator-based registration
# ---------------------------------------------------------------------------


class TestIbisBuilderDecorator:
    """@ibis_builder decorator registers a function in both registries."""

    def test_decorator_registers_in_extension_registry(self):
        @ibis_builder("_TestDecoratorExt")
        def _build_test_ext(criteria, ctx):
            return "ext_table"

        reg = get_registry()
        assert reg.get_ibis_builder("_TestDecoratorExt") is _build_test_ext

    def test_decorator_registers_in_execution_registry(self):
        @ibis_builder("_TestDecoratorExec")
        def _build_test_exec(criteria, ctx):
            return "exec_table"

        assert "_TestDecoratorExec" in _REGISTRY
        assert _REGISTRY["_TestDecoratorExec"] is _build_test_exec

    def test_decorator_preserves_function(self):
        @ibis_builder("_TestDecoratorPreserve")
        def _build_preserve(criteria, ctx):
            return "preserved"

        assert _build_preserve("c", "x") == "preserved"


# ---------------------------------------------------------------------------
# Programmatic registration
# ---------------------------------------------------------------------------


class TestProgrammaticRegistration:
    """ExtensionRegistry.register_ibis_builder works at runtime."""

    def test_register_and_retrieve(self):
        reg = get_registry()

        def my_builder(criteria, ctx):
            return "programmatic"

        reg.register_ibis_builder("_TestProgrammatic", my_builder)
        assert reg.get_ibis_builder("_TestProgrammatic") is my_builder

    def test_unregistered_returns_none(self):
        reg = get_registry()
        assert reg.get_ibis_builder("_NeverRegistered") is None


# ---------------------------------------------------------------------------
# Fallback in get_builder
# ---------------------------------------------------------------------------


class TestGetBuilderFallback:
    """get_builder falls back to the extension registry for unknown criteria."""

    def test_fallback_to_extension_registry(self):
        from circe.cohortdefinition.criteria import CriteriaGroup  # noqa: F401

        reg = get_registry()

        class _FallbackCriteria(Criteria):
            pass

        _FallbackCriteria.model_rebuild()

        def _fb_builder(criteria, ctx):
            return "fallback"

        reg.register_ibis_builder("_FallbackCriteria", _fb_builder)

        # Should be found via the extension registry fallback
        found = get_builder(_FallbackCriteria())
        assert found is _fb_builder

    def test_unknown_criteria_raises(self):
        from circe.cohortdefinition.criteria import CriteriaGroup  # noqa: F401

        class _UnknownCriteria(Criteria):
            pass

        _UnknownCriteria.model_rebuild()

        with pytest.raises(ValueError, match="No builder registered"):
            get_builder(_UnknownCriteria())


# ---------------------------------------------------------------------------
# Waveform builders registered via @ibis_builder
# ---------------------------------------------------------------------------


class TestWaveformIbisBuilders:
    """Waveform extension ibis builders are registered dynamically."""

    @pytest.fixture(autouse=True)
    def _import_waveform(self):
        import circe.extensions.waveform  # noqa: F401

    @pytest.mark.parametrize(
        "name",
        [
            "WaveformOccurrence",
            "WaveformRegistry",
            "WaveformChannelMetadata",
            "WaveformFeature",
        ],
    )
    def test_registered_in_extension_registry(self, name):
        reg = get_registry()
        builder = reg.get_ibis_builder(name)
        assert builder is not None
        assert callable(builder)

    @pytest.mark.parametrize(
        "name",
        [
            "WaveformOccurrence",
            "WaveformRegistry",
            "WaveformChannelMetadata",
            "WaveformFeature",
        ],
    )
    def test_registered_in_execution_registry(self, name):
        assert name in _REGISTRY
        assert callable(_REGISTRY[name])

    @pytest.mark.parametrize(
        "criteria_cls_name",
        [
            "WaveformOccurrence",
            "WaveformRegistry",
            "WaveformChannelMetadata",
            "WaveformFeature",
        ],
    )
    def test_get_builder_resolves(self, criteria_cls_name):
        from circe.extensions.waveform import criteria as wf_criteria

        cls = getattr(wf_criteria, criteria_cls_name)
        builder = get_builder(cls())
        assert callable(builder)
