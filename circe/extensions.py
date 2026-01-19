"""
Extension Registry for OMOP CDM.

This module provides the central registry for managing extensions to circe-py,
allowing external projects to register custom criteria classes, SQL builders,
and markdown renderers.
"""
from typing import Dict, List, Optional, Type, Set, Union
from pathlib import Path

# Forward references to avoid circular imports
# Actual imports happen inside methods or with TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cohortdefinition.criteria import Criteria
    from .cohortdefinition.builders.base import CriteriaSqlBuilder

class ExtensionRegistry:
    """Central registry for OMOP CDM extensions."""
    
    def __init__(self):
        # Maps criteria names to criteria classes (for JSON deserialization)
        self._criteria_classes: Dict[str, Type['Criteria']] = {}
        
        # Maps criteria types to SQL builder classes
        self._sql_builders: Dict[Type['Criteria'], Type['CriteriaSqlBuilder']] = {}
        
        # Maps criteria types to markdown template names
        self._markdown_templates: Dict[Type['Criteria'], str] = {}
        
        # List of paths to search for Jinja2 templates
        self._template_paths: List[Path] = []
    
    def register_criteria_class(self, name: str, cls: Type['Criteria']) -> None:
        """Register a new criteria class for JSON deserialization.
        
        Args:
            name: The name of the criteria type (e.g. "WaveformOccurrence")
            cls: The Criteria subclass
        """
        self._criteria_classes[name] = cls
    
    def register_sql_builder(self, criteria_cls: Type['Criteria'], builder_cls: Type['CriteriaSqlBuilder']) -> None:
        """Register a SQL builder for a criteria type.
        
        Args:
            criteria_cls: The Criteria subclass
            builder_cls: The CriteriaSqlBuilder subclass
        """
        self._sql_builders[criteria_cls] = builder_cls
    
    def register_markdown_template(self, criteria_cls: Type['Criteria'], template_name: str) -> None:
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
    
    def get_builder(self, criteria: 'Criteria') -> Optional['CriteriaSqlBuilder']:
        """Get the SQL builder for a criteria instance.
        
        Args:
            criteria: The criteria instance
            
        Returns:
            An instance of the registered SQL builder, or None if not found
        """
        builder_cls = self._sql_builders.get(type(criteria))
        return builder_cls() if builder_cls else None
    
    def get_template(self, criteria: 'Criteria') -> Optional[str]:
        """Get the markdown template name for a criteria instance.
        
        Args:
            criteria: The criteria instance
            
        Returns:
            The template name, or None if not found
        """
        return self._markdown_templates.get(type(criteria))
    
    def get_criteria_class(self, name: str) -> Optional[Type['Criteria']]:
        """Get a registered criteria class by name.
        
        Args:
            name: The name of the criteria type
            
        Returns:
            The Criteria subclass, or None if not found
        """
        return self._criteria_classes.get(name)
    
    @property
    def template_paths(self) -> List[Path]:
        """Get all registered template paths."""
        return list(self._template_paths)

# Global registry instance
_registry = ExtensionRegistry()

def get_registry() -> ExtensionRegistry:
    """Get the global extension registry instance."""
    return _registry
