"""
Extension Registry for OMOP CDM.

This module provides the central registry for managing extensions to circe-py,
allowing external projects to register custom criteria classes, SQL builders,
markdown renderers, and cohort builder domain methods.

Decorator Usage
---------------
Extension authors can use the provided decorator functions to register their
classes automatically, rather than calling the registry methods directly::

    from circe.extensions import criteria_class, sql_builder, markdown_template

    @criteria_class("WaveformOccurrence")
    class WaveformOccurrence(Criteria):
        ...

    @sql_builder(WaveformOccurrence)
    class WaveformOccurrenceSqlBuilder(CriteriaSqlBuilder):
        ...

    @markdown_template(WaveformOccurrence, "waveform_occurrence.j2")
    class WaveformOccurrenceMarkdownRenderer:
        ...

Domain Registration
-------------------
To also auto-generate cohort builder methods (with_X, require_X, etc.)::

    from circe.extensions import register_domain

    @register_domain(
        name="waveform_occurrence",
        domain="WaveformOccurrence",
        query_class=WaveformOccurrenceQuery,
    )
    class WaveformOccurrence(Criteria):
        ...
"""

from dataclasses import dataclass
from pathlib import Path

# Forward references to avoid circular imports
# Actual imports happen inside methods or with TYPE_CHECKING
from typing import TYPE_CHECKING, Callable, Optional, Union

if TYPE_CHECKING:
    from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
    from circe.cohortdefinition.criteria import Criteria


# ---------------------------------------------------------------------------
# DomainSpec: describes a complete OMOP domain for method generation
# ---------------------------------------------------------------------------


@dataclass
class DomainSpec:
    """Specification for a single OMOP domain type.

    Attributes:
        name: Short name used for builder method names
              (e.g. ``"condition"`` → ``with_condition``, ``require_condition``).
        domain: CIRCE domain key, also the JSON polymorphic key
                (e.g. ``"ConditionOccurrence"``).
        criteria_class: Pydantic model class for this domain.
        query_class: ``BaseQuery`` subclass for the fluent builder.
        requires_concept: ``False`` for domains like Death and
                          ObservationPeriod that don't need a concept set id.
    """

    name: str
    domain: str
    criteria_class: type
    query_class: type
    requires_concept: bool = True


# ---------------------------------------------------------------------------
# Global domain registry — populated by register_domain() and built-in init
# ---------------------------------------------------------------------------

_DOMAIN_REGISTRY: list[DomainSpec] = []


def get_domain_registry() -> list[DomainSpec]:
    """Return a snapshot of all registered domain specs."""
    return list(_DOMAIN_REGISTRY)


def _register_domain_spec(spec: DomainSpec) -> None:
    """Internal: add a DomainSpec and wire builder methods."""
    # Avoid duplicate registrations
    for existing in _DOMAIN_REGISTRY:
        if existing.domain == spec.domain:
            return
    _DOMAIN_REGISTRY.append(spec)
    _wire_builder_methods(spec)


# ---------------------------------------------------------------------------
# Builder method generation helpers
# ---------------------------------------------------------------------------


def _wire_builder_methods(spec: DomainSpec) -> None:
    """Generate with_X / require_X / exclude_X / censor_on_X on builder classes.

    Uses lazy imports to avoid circular dependencies — the builder module
    imports extensions at module load, so we defer the class lookups.
    """
    # Deferred imports to avoid circular dependencies with builder module
    try:
        from circe.cohort_builder.builder import (
            CohortBuilder,
            CohortWithCriteria,
            CohortWithEntry,
        )
        from circe.cohort_builder.query_builder import CriteriaGroupBuilder
    except ImportError:
        # Builder module not loaded yet — will be wired at builder init
        return

    name = spec.name
    query_cls = spec.query_class
    requires_concept = spec.requires_concept
    domain = spec.domain

    # If query_class is BaseQuery itself (not a subclass), we need to pass
    # domain as the first positional arg. Subclasses like ConditionQuery
    # hardcode their domain in __init__.
    from circe.cohort_builder.query_builder import BaseQuery as _BQ

    needs_domain = query_cls is _BQ

    # --- CohortBuilder.with_{name} ---
    if not hasattr(CohortBuilder, f"with_{name}"):
        if requires_concept:
            if needs_domain:

                def _make_entry(qc, dom):
                    def method(self, concept_set_id: int):
                        query = qc(dom, concept_set_id, is_entry=True)
                        cohort = CohortWithEntry(self, query)
                        query._parent = cohort
                        return cohort

                    return method
            else:

                def _make_entry(qc, dom):
                    def method(self, concept_set_id: int):
                        query = qc(concept_set_id, is_entry=True)
                        cohort = CohortWithEntry(self, query)
                        query._parent = cohort
                        return cohort

                    return method
        else:
            if needs_domain:

                def _make_entry(qc, dom):
                    def method(self):
                        query = qc(dom, is_entry=True)
                        return CohortWithEntry(self, query)

                    return method
            else:

                def _make_entry(qc, dom):
                    def method(self):
                        query = qc(is_entry=True)
                        return CohortWithEntry(self, query)

                    return method

        setattr(CohortBuilder, f"with_{name}", _make_entry(query_cls, domain))

    # --- CohortWithEntry.or_with_{name} ---
    if not hasattr(CohortWithEntry, f"or_with_{name}"):
        if requires_concept:
            if needs_domain:

                def _make_or_entry(qc, dom):
                    def method(self, concept_set_id: int):
                        query = qc(dom, concept_set_id, is_entry=True, parent=self)
                        self._entry_queries.append(query)
                        return self

                    return method
            else:

                def _make_or_entry(qc, dom):
                    def method(self, concept_set_id: int):
                        query = qc(concept_set_id, is_entry=True, parent=self)
                        self._entry_queries.append(query)
                        return self

                    return method
        else:
            if needs_domain:

                def _make_or_entry(qc, dom):
                    def method(self):
                        query = qc(dom, is_entry=True, parent=self)
                        self._entry_queries.append(query)
                        return self

                    return method
            else:

                def _make_or_entry(qc, dom):
                    def method(self):
                        query = qc(is_entry=True, parent=self)
                        self._entry_queries.append(query)
                        return self

                    return method

        setattr(CohortWithEntry, f"or_with_{name}", _make_or_entry(query_cls, domain))

    # --- CohortWithEntry delegate methods ---
    for action in ("require", "exclude", "censor_on"):
        method_name = f"{action}_{name}"
        if not hasattr(CohortWithEntry, method_name):

            def _make_delegate(act, n):
                if act == "censor_on":

                    def method(self, *args, **kwargs):
                        return getattr(self._to_criteria(), f"censor_on_{n}")(*args, **kwargs)
                elif act == "require":

                    def method(self, *args, **kwargs):
                        return getattr(self._to_criteria(), f"require_{n}")(*args, **kwargs)
                else:

                    def method(self, *args, **kwargs):
                        return getattr(self._to_criteria(), f"exclude_{n}")(*args, **kwargs)

                return method

            setattr(CohortWithEntry, method_name, _make_delegate(action, name))

    # Time-window kwargs that trigger auto-finalization
    _TIME_WINDOW_PARAMS = frozenset(
        [
            "anytime_before",
            "anytime_after",
            "within_days_before",
            "within_days_after",
            "within_days",
            "same_day",
            "during_event",
            "before_event_end",
        ]
    )

    # --- CohortWithCriteria.require_{name} / exclude_{name} / censor_on_{name} ---
    for action, is_exclusion, is_censor in [
        ("require", False, False),
        ("exclude", True, False),
        ("censor_on", False, True),
    ]:
        method_name = f"{action}_{name}"
        if not hasattr(CohortWithCriteria, method_name):
            if is_censor:
                if requires_concept:
                    if needs_domain:

                        def _make_censor(qc, dom, twp):
                            def method(self, concept_set_id: int, **kwargs):
                                query = qc(dom, concept_set_id, parent=self, is_censor=True)
                                if kwargs:
                                    query.apply_params(**kwargs)
                                    if any(p in kwargs for p in twp):
                                        return query._finalize()
                                return query

                            return method
                    else:

                        def _make_censor(qc, dom, twp):
                            def method(self, concept_set_id: int, **kwargs):
                                query = qc(concept_set_id, parent=self, is_censor=True)
                                if kwargs:
                                    query.apply_params(**kwargs)
                                    if any(p in kwargs for p in twp):
                                        return query._finalize()
                                return query

                            return method
                else:
                    if needs_domain:

                        def _make_censor(qc, dom, twp):
                            def method(self, concept_set_id: Optional[int] = None, **kwargs):
                                query = qc(dom, concept_set_id, parent=self, is_censor=True)
                                if kwargs:
                                    query.apply_params(**kwargs)
                                    if any(p in kwargs for p in twp):
                                        return query._finalize()
                                return query

                            return method
                    else:

                        def _make_censor(qc, dom, twp):
                            def method(self, concept_set_id: Optional[int] = None, **kwargs):
                                query = qc(concept_set_id, parent=self, is_censor=True)
                                if kwargs:
                                    query.apply_params(**kwargs)
                                    if any(p in kwargs for p in twp):
                                        return query._finalize()
                                return query

                            return method

                setattr(CohortWithCriteria, method_name, _make_censor(query_cls, domain, _TIME_WINDOW_PARAMS))
            else:
                if requires_concept:
                    if needs_domain:

                        def _make_criteria(qc, dom, excl, twp):
                            def method(self, concept_set_id: int, **kwargs):
                                query = qc(dom, concept_set_id, parent=self, is_exclusion=excl)
                                if kwargs:
                                    query.apply_params(**kwargs)
                                    if any(p in kwargs for p in twp):
                                        return query._finalize()
                                return query

                            return method
                    else:

                        def _make_criteria(qc, dom, excl, twp):
                            def method(self, concept_set_id: int, **kwargs):
                                query = qc(concept_set_id, parent=self, is_exclusion=excl)
                                if kwargs:
                                    query.apply_params(**kwargs)
                                    if any(p in kwargs for p in twp):
                                        return query._finalize()
                                return query

                            return method
                else:
                    if needs_domain:

                        def _make_criteria(qc, dom, excl, twp):
                            def method(self, **kwargs):
                                query = qc(dom, parent=self, is_exclusion=excl)
                                if kwargs:
                                    query.apply_params(**kwargs)
                                    if any(p in kwargs for p in twp):
                                        return query._finalize()
                                return query

                            return method
                    else:

                        def _make_criteria(qc, dom, excl, twp):
                            def method(self, **kwargs):
                                query = qc(parent=self, is_exclusion=excl)
                                if kwargs:
                                    query.apply_params(**kwargs)
                                    if any(p in kwargs for p in twp):
                                        return query._finalize()
                                return query

                            return method

                setattr(
                    CohortWithCriteria,
                    method_name,
                    _make_criteria(query_cls, domain, is_exclusion, _TIME_WINDOW_PARAMS),
                )

    # --- CriteriaGroupBuilder.require_{name} / exclude_{name} ---
    for action, is_exclusion in [("require", False), ("exclude", True)]:
        method_name = f"{action}_{name}"
        if not hasattr(CriteriaGroupBuilder, method_name):
            if requires_concept:
                if needs_domain:

                    def _make_group(qc, dom, excl, twp):
                        def method(self, concept_set_id: int, **kwargs):
                            query = qc(dom, concept_set_id, parent=self, is_exclusion=excl)
                            if kwargs:
                                query.apply_params(**kwargs)
                                if any(p in kwargs for p in twp):
                                    return query._finalize()
                            return query

                        return method
                else:

                    def _make_group(qc, dom, excl, twp):
                        def method(self, concept_set_id: int, **kwargs):
                            query = qc(concept_set_id, parent=self, is_exclusion=excl)
                            if kwargs:
                                query.apply_params(**kwargs)
                                if any(p in kwargs for p in twp):
                                    return query._finalize()
                            return query

                        return method
            else:
                if needs_domain:

                    def _make_group(qc, dom, excl, twp):
                        def method(self, **kwargs):
                            query = qc(dom, parent=self, is_exclusion=excl)
                            if kwargs:
                                query.apply_params(**kwargs)
                                if any(p in kwargs for p in twp):
                                    return query._finalize()
                            return query

                        return method
                else:

                    def _make_group(qc, dom, excl, twp):
                        def method(self, **kwargs):
                            query = qc(parent=self, is_exclusion=excl)
                            if kwargs:
                                query.apply_params(**kwargs)
                                if any(p in kwargs for p in twp):
                                    return query._finalize()
                            return query

                        return method

            setattr(
                CriteriaGroupBuilder,
                method_name,
                _make_group(query_cls, domain, is_exclusion, _TIME_WINDOW_PARAMS),
            )


# ---------------------------------------------------------------------------
# Helpers that replace duplicated criteria_class_map / domain_map dicts
# ---------------------------------------------------------------------------


def get_criteria_class_map() -> dict[str, type]:
    """Return {domain_string: criteria_class} merging built-ins + extensions.

    Replaces the hand-written ``NAMES_TO_CLASSES``, ``criteria_class_map``,
    and ``domain_map`` dicts that were duplicated across the codebase.
    """
    # Start with extension-registered criteria classes
    result = dict(_registry._criteria_classes)
    # Add domain-registry entries (built-in + extension domains)
    for spec in _DOMAIN_REGISTRY:
        result.setdefault(spec.domain, spec.criteria_class)
    return result


def get_sql_builder_map() -> dict[type, type]:
    """Return {criteria_class: sql_builder_class} for all registered domains.

    Used by ``CohortExpressionQueryBuilder`` to replace the isinstance chain.
    """
    return dict(_registry._sql_builders)


# ---------------------------------------------------------------------------
# ExtensionRegistry class
# ---------------------------------------------------------------------------


class ExtensionRegistry:
    """Central registry for OMOP CDM extensions."""

    def __init__(self):
        # Maps criteria names to criteria classes (for JSON deserialization)
        self._criteria_classes: dict[str, type[Criteria]] = {}

        # Maps criteria types to SQL builder classes
        self._sql_builders: dict[type[Criteria], type[CriteriaSqlBuilder]] = {}

        # Maps criteria types to markdown template names
        self._markdown_templates: dict[type[Criteria], str] = {}

        # List of paths to search for Jinja2 templates
        self._template_paths: list[Path] = []

    def register_criteria_class(self, name: str, cls: type["Criteria"]) -> None:
        """Register a new criteria class for JSON deserialization.

        Args:
            name: The name of the criteria type (e.g. "WaveformOccurrence")
            cls: The Criteria subclass
        """
        self._criteria_classes[name] = cls

    def register_sql_builder(
        self,
        criteria_cls: type["Criteria"],
        builder_cls: type["CriteriaSqlBuilder"],
    ) -> None:
        """Register a SQL builder for a criteria type.

        Args:
            criteria_cls: The Criteria subclass
            builder_cls: The CriteriaSqlBuilder subclass
        """
        self._sql_builders[criteria_cls] = builder_cls

    def register_markdown_template(self, criteria_cls: type["Criteria"], template_name: str) -> None:
        """Register a Jinja2 template for markdown rendering.

        Args:
            criteria_cls: The Criteria subclass
            template_name: The name of the template file (e.g. "waveform_occurrence.j2")
        """
        self._markdown_templates[criteria_cls] = template_name

    def add_template_path(self, path: Path) -> None:
        """Add a path to search for Jinja2 templates.

        Args:
            path: Path to a directory containing Jinja2 templates
        """
        if path not in self._template_paths:
            self._template_paths.append(path)

    def get_builder(self, criteria: "Criteria") -> Optional["CriteriaSqlBuilder"]:
        """Get the SQL builder for a criteria instance.

        Args:
            criteria: The criteria instance

        Returns:
            An instance of the registered SQL builder, or None if not found
        """
        builder_cls = self._sql_builders.get(type(criteria))
        return builder_cls() if builder_cls else None

    def get_template(self, criteria: "Criteria") -> Optional[str]:
        """Get the markdown template name for a criteria instance.

        Args:
            criteria: The criteria instance

        Returns:
            The template name, or None if not found
        """
        return self._markdown_templates.get(type(criteria))

    def get_criteria_class(self, name: str) -> Optional[type["Criteria"]]:
        """Get a registered criteria class by name.

        Args:
            name: The name of the criteria type

        Returns:
            The Criteria subclass, or None if not found
        """
        return self._criteria_classes.get(name)

    @property
    def template_paths(self) -> list[Path]:
        """Get all registered template paths."""
        return list(self._template_paths)


# Global registry instance
_registry = ExtensionRegistry()


def get_registry() -> ExtensionRegistry:
    """Get the global extension registry instance."""
    return _registry


# ---------------------------------------------------------------------------
# Decorator helpers
# ---------------------------------------------------------------------------


def criteria_class(name: str) -> "Callable[[type['Criteria']], type['Criteria']]":
    """Class decorator that registers a Criteria subclass for JSON deserialization.

    Args:
        name: The criteria type name used as the JSON key
              (e.g. ``"WaveformOccurrence"``).

    Example::

        @criteria_class("WaveformOccurrence")
        class WaveformOccurrence(Criteria):
            ...
    """

    def decorator(cls: "type['Criteria']") -> "type['Criteria']":
        _registry.register_criteria_class(name, cls)  # type: ignore[arg-type]
        return cls

    return decorator  # type: ignore[return-value]


def sql_builder(
    criteria_cls: "type['Criteria']",
) -> "Callable[[type['CriteriaSqlBuilder']], type['CriteriaSqlBuilder']]":
    """Class decorator that registers a SQL builder for a given Criteria type.

    Args:
        criteria_cls: The Criteria subclass this builder handles.

    Example::

        @sql_builder(WaveformOccurrence)
        class WaveformOccurrenceSqlBuilder(CriteriaSqlBuilder):
            ...
    """

    def decorator(builder_cls: "type['CriteriaSqlBuilder']") -> "type['CriteriaSqlBuilder']":
        _registry.register_sql_builder(criteria_cls, builder_cls)  # type: ignore[arg-type]
        return builder_cls

    return decorator  # type: ignore[return-value]


def markdown_template(criteria_cls: "type['Criteria']", template_name: str) -> "Callable[[type], type]":
    """Class decorator that registers a Jinja2 markdown template for a Criteria type.

    Args:
        criteria_cls: The Criteria subclass this template renders.
        template_name: Filename of the Jinja2 template
                       (e.g. ``"waveform_occurrence.j2"``).

    Example::

        @markdown_template(WaveformOccurrence, "waveform_occurrence.j2")
        class WaveformOccurrenceMarkdownRenderer:
            ...
    """

    def decorator(cls: type) -> type:
        _registry.register_markdown_template(criteria_cls, template_name)  # type: ignore[arg-type]
        return cls

    return decorator


def register_domain(
    *, name: str, domain: str, query_class: type, requires_concept: bool = True
) -> "Callable[[type['Criteria']], type['Criteria']]":
    """Class decorator that registers a domain for builder method generation.

    Combines ``@criteria_class`` registration with automatic generation of
    ``with_X``, ``require_X``, ``exclude_X``, and ``censor_on_X`` methods
    on all cohort builder classes.

    Args:
        name: Short name for method generation
              (e.g. ``"waveform_occurrence"`` → ``with_waveform_occurrence``).
        domain: CIRCE domain key (e.g. ``"WaveformOccurrence"``).
        query_class: ``BaseQuery`` subclass for the fluent builder.
        requires_concept: ``False`` for domains without concept set ids.

    Example::

        @register_domain(
            name="waveform_occurrence",
            domain="WaveformOccurrence",
            query_class=WaveformOccurrenceQuery,
        )
        class WaveformOccurrence(Criteria):
            ...
    """

    def decorator(cls: "type['Criteria']") -> "type['Criteria']":
        # Register for JSON deserialization
        _registry.register_criteria_class(domain, cls)  # type: ignore[arg-type]
        # Register as a full domain with builder method generation
        spec = DomainSpec(
            name=name,
            domain=domain,
            criteria_class=cls,
            query_class=query_class,
            requires_concept=requires_concept,
        )
        _register_domain_spec(spec)
        return cls

    return decorator  # type: ignore[return-value]


def template_path(path: Union[str, Path]) -> None:
    """Register a directory as a template search path.

    This is a convenience function (not a decorator) that adds *path* to the
    global registry so that Jinja2 can locate extension templates.

    Args:
        path: Path to a directory containing Jinja2 templates.

    Example::

        template_path(Path(__file__).parent / "templates")
    """
    _registry.add_template_path(Path(path))
