"""
Extension Registry for OMOP CDM.

This module provides the central registry for managing extensions to circe-py,
allowing external projects to register custom criteria classes, SQL builders,
and markdown renderers.
"""
from typing import Dict, List, Optional, Type, Set, Union, Any
from pathlib import Path
import importlib.metadata

# Forward references to avoid circular imports
# Actual imports happen inside methods or with TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cohortdefinition.criteria import Criteria
    from .cohortdefinition.builders.base import CriteriaSqlBuilder
    from collections.abc import Callable

class ExtensionRegistry:
    """Central registry for OMOP CDM extensions."""
    
    def __init__(self):
        # Maps criteria names to criteria classes (for JSON deserialization)
        self._criteria_classes: Dict[str, Type['Criteria']] = {}
        
        # Maps criteria types to SQL builder classes
        self._sql_builders: Dict[Type['Criteria'], Type['CriteriaSqlBuilder']] = {}
        
        # Maps criteria names to Ibis builder functions
        self._ibis_builders: Dict[str, 'Callable'] = {}
        
        # Maps criteria types to markdown template names
        self._markdown_templates: Dict[Type['Criteria'], str] = {}
        
        # List of paths to search for Jinja2 templates
        self._template_paths: List[Path] = []

        # Maps extension names to their versions
        self._named_extensions: Dict[str, str] = {}
        
        # Maps domain names to query builder classes (for EvaluationBuilder)
        self._domain_queries: Dict[str, Type[Any]] = {}
        
        # Flag to track if entry points have been loaded
        self._loaded_entry_points = False
    
    def register_named_extension(self, name: str, version: str = "0.0.0") -> None:
        """Register a named extension with its version.
        
        Args:
            name: The unique name of the extension
            version: The version string
        """
        self._named_extensions[name] = version

    def get_registered_extension_names(self) -> Set[str]:
        """Get the set of names of all registered extensions.
        
        Returns:
            A set of extension names.
        """
        return set(self._named_extensions.keys())

    def register_criteria_class(self, name: str, cls: Type['Criteria']) -> None:
        """Register a new criteria class for JSON deserialization.
        
        Args:
            name: The name of the criteria type (e.g. "WaveformOccurrence")
            cls: The Criteria subclass
        """
        self._criteria_classes[name] = cls
    
    def get_all_criteria_classes(self, base_map: Dict[str, Type['Criteria']]) -> Dict[str, Type['Criteria']]:
        """Merge a base criteria map with all registered extension criteria classes.
        
        Args:
            base_map: The core criteria name -> class map
            
        Returns:
            A unified dictionary containing both built-in and extension criteria.
        """
        unified = dict(base_map)
        unified.update(self._criteria_classes)
        return unified

    def register_sql_builder(self, criteria_cls: Type['Criteria'], builder_cls: Type['CriteriaSqlBuilder']) -> None:
        """Register a SQL builder for a criteria type.
        
        Args:
            criteria_cls: The Criteria subclass
            builder_cls: The CriteriaSqlBuilder subclass
        """
        self._sql_builders[criteria_cls] = builder_cls
        
    def register_ibis_builder(self, criteria_name: str, builder_func: 'Callable') -> None:
        """Register an Ibis builder for a criteria type name.
        
        Args:
            criteria_name: The name of the Criteria subclass
            builder_func: The function that builds the Ibis table for this criteria
        """
        self._ibis_builders[criteria_name] = builder_func
    
    def register_markdown_template(self, criteria_cls: Type['Criteria'], template_name: str) -> None:
        """Register a Jinja2 template for markdown rendering.
        
        Args:
            criteria_cls: The Criteria subclass
            template_name: The name of the template file (e.g. "waveform_occurrence.j2")
        """
        self._markdown_templates[criteria_cls] = template_name
    
    def register_domain_query(self, domain_name: str, query_class: Type[Any], criteria_class: Optional[Type['Criteria']] = None) -> None:
        """Register a domain query builder for EvaluationBuilder.
        
        Args:
            domain_name: The name of the domain (e.g. "waveform")
            query_class: The query builder class
            criteria_class: Optional criteria class associated with this domain
        """
        self._domain_queries[domain_name] = query_class
        if criteria_class:
            self.register_criteria_class(domain_name, criteria_class)

    def get_domain_query_map(self) -> Dict[str, Type[Any]]:
        """Get all registered domain query builder classes.
        
        Returns:
            A dictionary mapping domain names to query builder classes.
        """
        return dict(self._domain_queries)

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
        
    def get_ibis_builder(self, criteria_name: str) -> Optional['Callable']:
        """Get the Ibis builder for a criteria name.
        
        Args:
            criteria_name: The name of the criteria type
            
        Returns:
            The registered Ibis builder function, or None if not found
        """
        return self._ibis_builders.get(criteria_name)
    
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

    def load_entry_point_extensions(self) -> None:
        """Discover and load extensions via Python entry points."""
        if self._loaded_entry_points:
            return
            
        self._loaded_entry_points = True
        
        # In Python 3.10+, entry_points() returns an EntryPoints object that is selectable
        # For older versions, it returns a dict.
        eps = importlib.metadata.entry_points()
        if hasattr(eps, 'select'):
            group_eps = eps.select(group='circe.extensions')
        else:
            # Fallback for older importlib_metadata or Python < 3.10 if eps is a dict
            group_eps = eps.get('circe.extensions', [])
            
        for entry_point in group_eps:
            try:
                register_func = entry_point.load()
                register_func()
            except Exception:
                # Silently fail for now, or consider logging
                pass
                
        # Validate that all registered criteria have a corresponding SQL builder
        for name, cls in self._criteria_classes.items():
            if cls not in self._sql_builders:
                raise NotImplementedError(
                    f"Criteria {name} is registered but lacks a SQL builder. "
                    "Extension developers must provide a SQL builder implementation "
                    "using @register_sql_builder."
                )

# Global registry instance
_registry = ExtensionRegistry()

def get_registry() -> ExtensionRegistry:
    """Get the global extension registry instance with lazy loading of entry points."""
    if not _registry._loaded_entry_points:
        _registry.load_entry_point_extensions()
    return _registry


def _snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase. E.g. 'waveform_feature' -> 'WaveformFeature'."""
    return ''.join(word.capitalize() for word in name.split('_'))


def _pascal_to_snake(name: str) -> str:
    """Convert PascalCase to snake_case. E.g. 'WaveformFeature' -> 'waveform_feature'."""
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def _make_query_class(domain_name: str, criteria_cls: type) -> type:
    """Dynamically create a BaseQuery subclass from a Criteria class.
    
    The generated class:
    - Sets domain=domain_name in __init__
    - Overrides apply_params to store criteria-field-matching kwargs in config.extra_fields
    
    Args:
        domain_name: PascalCase domain name (e.g. 'WaveformFeature')
        criteria_cls: The Criteria subclass to introspect
        
    Returns:
        A new BaseQuery subclass
    """
    from circe.cohort_builder.query_builder import BaseQuery
    
    # Introspect the criteria's Pydantic fields
    field_names = set(criteria_cls.model_fields.keys())
    
    def _init(self, concept_set_id=None, **kwargs):
        BaseQuery.__init__(self, domain_name, concept_set_id, **kwargs)
    
    def _apply_params(self, **kwargs):
        BaseQuery.apply_params(self, **kwargs)
        # Store any kwarg that matches a criteria field in extra_fields
        for key, val in kwargs.items():
            if key in field_names:
                self._config.extra_fields[key] = val
        return self
    
    query_cls = type(
        f"{domain_name}Query",
        (BaseQuery,),
        {
            '__init__': _init,
            'apply_params': _apply_params,
        }
    )
    return query_cls


def register_criteria(domain_name: str = None, extension: str = None, template: str = None):
    """Decorator that auto-registers a Criteria subclass and generates its fluent query class.
    
    This replaces the manual pattern of:
        1. registry.register_criteria_class("MyDomain", MyDomain)
        2. Writing a BaseQuery subclass
        3. registry.register_domain_query("MyDomain", MyDomainQuery)
        4. registry.register_markdown_template(MyDomain, "my_domain.j2")
    
    Usage::
    
        @register_criteria(extension="waveform", template="waveform_occurrence.j2")
        class WaveformOccurrence(Criteria):
            ...
    
    Args:
        domain_name: Override the domain name (defaults to the class name)
        extension: The extension name this criteria belongs to (e.g. "waveform")
        template: Jinja2 template filename for markdown rendering (e.g. "waveform_occurrence.j2").
                  The templates/ directory relative to the criteria module is auto-discovered.
    """
    def decorator(cls):
        import inspect
        from pathlib import Path
        
        name = domain_name or cls.__name__
        registry = get_registry()
        
        # 1. Register the criteria class
        registry.register_criteria_class(name, cls)
        
        # 2. Auto-generate and register a BaseQuery subclass
        query_cls = _make_query_class(name, cls)
        registry.register_domain_query(name, query_cls, criteria_class=cls)
        
        # 3. Register markdown template if provided
        if template:
            cls_file = inspect.getfile(cls)
            template_dir = Path(cls_file).parent / "templates"
            if template_dir.is_dir():
                registry.add_template_path(template_dir)
            registry.register_markdown_template(cls, template)
        
        # 4. Stash metadata on the class for introspection
        cls._circe_domain = name
        cls._circe_query_class = query_cls
        if extension:
            cls._circe_extension = extension
        
        return cls
    return decorator


def register_sql_builder(criteria_class):
    """Decorator that auto-registers a CriteriaSqlBuilder for a Criteria class.
    
    Usage::
    
        @register_sql_builder(WaveformOccurrence)
        class WaveformOccurrenceSqlBuilder(CriteriaSqlBuilder[WaveformOccurrence]):
            ...
    
    Args:
        criteria_class: The Criteria subclass this builder handles
    """
    def decorator(cls):
        registry = get_registry()
        registry.register_sql_builder(criteria_class, cls)
        cls._circe_criteria_class = criteria_class
        return cls
    return decorator


def register_ibis_builder(criteria_name: str):
    """Decorator that registers an Ibis execution builder for a criteria class by name.
    
    Usage::
    
        @register_ibis_builder("WaveformOccurrence")
        def build_waveform_occurrence(criteria: WaveformOccurrence, ctx: BuildContext):
            ...
            
    Args:
        criteria_name: The string name of the Criteria subclass this builder handles
    """
    def decorator(func):
        registry = get_registry()
        registry.register_ibis_builder(criteria_name, func)
        return func
    return decorator
