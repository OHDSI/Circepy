"""
Bootstrapping CIRCE for use via reticulate in R.

This script:
- Imports all submodules of circe automatically
- Finds all Pydantic `BaseModel` subclasses
- Calls `model_rebuild()` on each to avoid the call stack depth issue
  when creating CIRCE objects from R.
"""

import pkgutil
import importlib
import inspect
import circe
from pydantic import BaseModel

def rebuild_all_pydantic_models(package):
    for loader, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            continue

        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and issubclass(obj, BaseModel):
                try:
                    obj.model_rebuild(raise_errors=False)
                    # Eager instantiation with no args if possible
                    try:
                        obj()
                    except Exception:
                        pass
                except Exception:
                    pass

# Run
rebuild_all_pydantic_models(circe)

