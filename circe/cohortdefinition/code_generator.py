
from typing import Any, List, Set, Type
import textwrap
from enum import Enum
from pydantic import BaseModel
from .cohort import CohortExpression, ConceptSet
from .criteria import Criteria, CriteriaGroup
from .core import Period

def to_python_code(obj: Any) -> str:
    """
    Converts a CohortExpression (or any circe model) into a human-readable Python code string 
    that instantiates the object.
    """
    imports: Set[str] = set()
    
    def _collect_imports(o: Any):
        if hasattr(o, '__module__') and hasattr(o, '__name__') and o.__module__.startswith('circe.'):
             # Try to import from the top level class map if possible, but for now specific modules
             imports.add(f"from {o.__module__} import {o.__class__.__name__}")
        
        if hasattr(o, 'model_dump'):
            # Access model_fields from the class, not the instance
            for name, field in o.__class__.model_fields.items():
                val = getattr(o, name)
                if val is not None:
                    if isinstance(val, list):
                        for item in val:
                             _collect_imports(item)
                    else:
                        _collect_imports(val)

    # Initial pass to collect some imports - though we might just rely on a standard set or dynamic approach
    # For a robust generator, we might want to just handle the traversal and printing, 
    # and maybe return imports separately? 
    # Let's do the string generation directly.
    
    lines = []
    
    # We will build a set of required imports as we traverse
    required_classes = set()

    def _repr(o: Any, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        
        if o is None:
            return "None"
        
        if instance_is_pydantic(o):
            required_classes.add(o.__class__)
            cls_name = o.__class__.__name__
            
            # Get set fields
            fields = {}
            # Access model_fields from the class
            for name, field_info in o.__class__.model_fields.items():
                val = getattr(o, name)
                # Check for defaults?
                # Pydantic V2 doesn't have a simple "is_set" for fields without model_dump(exclude_unset)
                # But we want to preserve structure even if it matches default maybe? 
                # Let's stick to non-None for now as per plan
                if val is not None:
                     # Check if it equals default
                     if val != field_info.get_default():
                         fields[name] = val
            
            if not fields:
                 return f"{cls_name}()"

            args = []
            for name, val in fields.items():
                formatted_val = _repr(val, indent_level + 1)
                args.append(f"{name}={formatted_val}")
            
            # Format nicely
            # If arguments are short, inline them. If long, multiline.
            # Simple heuristic: if any arg value has a newline, or total length > 80, go multiline
            
            inner_str = ", ".join(args)
            if len(inner_str) > 80 or "\n" in inner_str:
                joiner = f",\n{indent}    "
                field_strs = [f"{name}={_repr(val, indent_level + 1)}" for name, val in fields.items()]
                return f"{cls_name}(\n{indent}    {joiner.join(field_strs)}\n{indent})"
            else:
                 return f"{cls_name}({inner_str})"

        elif isinstance(o, list):
            if not o:
                return "[]"
            
            items = [_repr(i, indent_level + 1) for i in o]
            inner_str = ", ".join(items)
            
            if len(inner_str) > 60 or "\n" in inner_str:
                 joiner = f",\n{indent}    "
                 return f"[\n{indent}    {joiner.join(items)}\n{indent}]"
            return f"[{inner_str}]"
            
        elif isinstance(o, Enum):
            required_classes.add(o.__class__)
            return f"{o.__class__.__name__}.{o.name}"
            
        elif isinstance(o, str):
            # Use repr to handle quotes and escaping safely
            return repr(o)
            
        else:
            return repr(o)

    def instance_is_pydantic(o):
        return hasattr(o, 'model_dump')

    code_body = _repr(obj)
    
    # Generate Imports
    import_lines = []
    # Group by module
    module_map = {}
    for cls in required_classes:
        mod = cls.__module__
        if mod not in module_map:
            module_map[mod] = []
        module_map[mod].append(cls.__name__)
    
    for mod in sorted(module_map.keys()):
        classes = sorted(module_map[mod])
        import_lines.append(f"from {mod} import {', '.join(classes)}")
    
    return "\n".join(import_lines) + "\n\n" + "cohort = " + code_body

def save_to_file(obj: Any, filename: str) -> None:
    """
    Generates Python code for the object and saves it to a file.
    """
    code = to_python_code(obj)
    with open(filename, 'w') as f:
        f.write(code)

