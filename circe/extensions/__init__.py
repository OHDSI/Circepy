"""
Extension Registry for OMOP CDM.

This module provides the central registry for managing extensions to circe-py,
allowing external projects to register custom criteria classes, SQL builders,
and markdown renderers.

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
"""

from pathlib import Path

# Forward references to avoid circular imports
# Actual imports happen inside methods or with TYPE_CHECKING
from typing import TYPE_CHECKING, Callable, Optional, Union

if TYPE_CHECKING:
    from .cohortdefinition.builders.base import CriteriaSqlBuilder
    from .cohortdefinition.criteria import Criteria


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
